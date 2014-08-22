# Copyright 2010 Mike Wakerly <opensource@hoho.com>
#
# This file is part of the Pykeg package of the Kegbot project.
# For more information on Pykeg or Kegbot, see http://kegbot.org/
#
# Pykeg is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Pykeg is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pykeg.  If not, see <http://www.gnu.org/licenses/>.

"""Tap (single path of fluid) management module."""

from __future__ import absolute_import

import datetime
import gflags
import inspect
import requests
import time
import threading
import logging

from . import backend
from . import common_defs
from . import kbevent
from . import kegnet
from .flow import Flow
from .flow_meter import FlowMeter
from .tap import Tap

from kegbot.api import kbapi
from kegbot.util import util

FLAGS = gflags.FLAGS


def EventHandler(event_type):
  def decorate(f):
    if not hasattr(f, 'events'):
      f.events = set()
    f.events.add(event_type)
    return f
  return decorate


class Manager(object):
  def __init__(self, event_hub):
    self._name = self.__class__.__name__
    self._event_hub = event_hub
    self._logger = logging.getLogger(self._name)

  def GetEventHandlers(self):
    ret = {}
    for name, method in inspect.getmembers(self, inspect.ismethod):
      if not hasattr(method, 'events'):
        continue
      for event_type in method.events:
        if event_type not in ret:
          ret[event_type] = set()
        ret[event_type].add(method)
    return ret

  def _PublishEvent(self, event):
    """Convenience alias for EventHub.PublishEvent"""
    self._event_hub.PublishEvent(event)


class TapManager(Manager):
  """Maintains listing of available fluid paths.

  This manager maintains the set of available beer taps.  Taps have a
  one-to-one correspondence with beer taps.  For example, a kegboard controller
  is capable of reading from two flow sensors; thus, it provides two beer
  taps.
  """

  def __init__(self, event_hub, backend_obj):
    super(TapManager, self).__init__(event_hub)
    self._backend = backend_obj
    self._taps = {}

  def GetAllTaps(self):
    return self._taps.values()

  def _RegisterOrUpdateTap(self, name, ml_per_tick, relay_name=None):
    existing = self._taps.get(name)
    new_tap = Tap(name, ml_per_tick, relay_name)
    if existing == new_tap:
      return
    self._logger.info('Updating tap: %s' % new_tap)
    self._taps[name] = new_tap

  def _RemoveTap(self, name):
    tap = self._taps.get(name)
    self.logger.info('Removing tap: %s' % tap)
    del self._taps[name]
    del self._meters[name]

  def GetTap(self, name):
    """Returns the registered tap identified by `name`, or None."""
    return self._taps.get(name)

  @EventHandler(kbevent.SyncEvent)
  def _HandleSync(self, event):
    new_taps = event.data.get('taps', [])

    for tap in new_taps:
      self._RegisterOrUpdateTap(tap.meter_name, tap.ml_per_tick,
          relay_name=tap.relay_name)

  @EventHandler(kbevent.ControllerConnectedEvent)
  def _HandleControllerConnected(self, event):
    try:
      controller = self._backend.CreateController(event.controller_name)
      self._logger.info('Created new controller: {}'.format(controller))
    except backend.BackendException as e:
      self._logger.info('Not creating controller: {}'.format(e))

class FlowManager(Manager):
  """Class reponsible for maintaining and servicing flows."""
  def __init__(self, event_hub, tap_manager):
    super(FlowManager, self).__init__(event_hub)
    self._tap_manager = tap_manager
    self._meters = {}
    self._flow_map = {}
    self._logger = logging.getLogger("flowmanager")
    self._next_flow_id = int(time.time())
    self._lock = threading.Lock()

  @util.synchronized
  def _GetNextFlowId(self):
    """Returns the next usable flow identifier.

    Flow IDs are simply sequence numbers, used around the core to disambiguate
    flows."""
    ret = self._next_flow_id
    self._next_flow_id += 1
    return ret

  @util.synchronized
  def GetMeter(self, meter_name):
    m = self._meters.get(meter_name)
    if not m:
      m = FlowMeter(meter_name, 1000.0)
      self._meters[meter_name] = m
    return m

  def GetActiveFlows(self):
    return self._flow_map.values()

  def IterIdleFlows(self, when=None):
    for flow in self._flow_map.values():
      if flow.IsIdle(when):
        yield flow

  def GetFlow(self, tap_name):
    return self._flow_map.get(tap_name)

  def StartFlow(self, meter_name, username='', max_idle_secs=10):
    """Starts a new flow on the given meter, or takes over the existing flow.

    Args
      meter_name: name of the meter producing the flow
      username: username to own the flow, or None/empty string for anonymous
      max_idle_secs: maximum number of seconds until the flow is marked idle

    Returns
      Tuple of (Flow, boolean is_new).
    """
    current = self.GetFlow(meter_name)
    if current and username:
      if current.GetUsername() == username:
        # Already have a flow for this user; no change.
        return current, False
      elif current.GetUsername() == '':
        # Take over existing anonymous flow.
        self._logger.info('User "%s" is taking over the existing flow' %
            username)
        current.SetUsername(username)
        self._PublishUpdate(current)
        return current, False
      else:
        self._logger.info('User "%s" is replacing the existing flow' %
            username)
        self.StopFlow(meter_name)

    # Start a new flow.
    new_flow = Flow(meter_name, flow_id=self._GetNextFlowId(), username=username,
        max_idle_secs=max_idle_secs)
    self._flow_map[meter_name] = new_flow
    self._logger.info('Starting flow: %s' % new_flow)
    self._PublishUpdate(new_flow)

    # Open up the relay if the flow is authenticated.
    if username:
      self._PublishRelayEvent(new_flow, enable=True)
    return new_flow, True

  def StopFlow(self, meter_name):
    """Ends the flow at the given meter name.

    Returns
      the previously active flow, or None if no flow was active.
    """
    flow = self.GetFlow(meter_name)
    if not flow:
      self._logger.warning('No flow to stop on meter %s' % meter_name)
      return None

    self._logger.info('Stopping flow: %s' % flow)
    self._PublishRelayEvent(flow, enable=False)
    del self._flow_map[meter_name]
    self._StateChange(flow, kbevent.FlowUpdate.FlowState.COMPLETED)
    return flow

  def UpdateFlow(self, meter_name, meter_reading, when=None):
    """Creates or updates a flow at `meter_name`.

    Args
      meter_name: name of the tap to update
      meter_reading: instantaneous meter reading
      when: timestamp used for activity (defaults to datetime.now)

    Returns
      Tuple of (flow, is_new).
      Flow may be None if no update occurred.
    """
    meter = self.GetMeter(meter_name)
    tap = self._tap_manager.GetTap(meter_name)
    delta = meter.SetTicks(meter_reading)
    self._logger.debug('Flow update: tap=%s meter_reading=%i (delta=%i)' %
        (meter_name, meter_reading, delta))

    is_new = False
    flow = self.GetFlow(meter_name)
    if flow is None:
      self._logger.debug('Starting flow implicitly due to activity.')
      flow, is_new = self.StartFlow(meter_name)
    if when is None:
      when = datetime.datetime.now()

    flow.AddTicks(delta, when, tap)
    self._PublishUpdate(flow)
    return flow, is_new

  def _StateChange(self, flow, new_state):
    flow.SetState(new_state)
    self._PublishUpdate(flow)

  def _PublishUpdate(self, flow):
    event = flow.GetUpdateEvent()
    self._PublishEvent(event)

  @EventHandler(kbevent.MeterUpdate)
  def HandleFlowActivityEvent(self, event):
    flow_instance, is_new = self.UpdateFlow(event.meter_name, event.reading)

  @EventHandler(kbevent.HeartbeatSecondEvent)
  def _HandleHeartbeatEvent(self, event):
    for flow in self.GetActiveFlows():
      if flow.IsIdle():
        self._logger.info('Flow has become too idle, ending: %s' % flow)
        self._StateChange(flow, kbevent.FlowUpdate.FlowState.IDLE)
        self.StopFlow(flow.GetMeterName())
      else:
        if flow.GetUsername():
          self._PublishRelayEvent(flow, enable=True)

  def _PublishRelayEvent(self, flow, enable=True):
    self._logger.debug('Publishing relay event: flow=%s, enable=%s' % (flow,
        enable))
    tap = self._tap_manager.GetTap(flow.GetMeterName())
    if not tap:
      # Unknown meter; don't attempt to enable any relays for it
      # since we don't know its configuration.
      return

    relay = tap.GetRelayName()
    if not relay:
      self._logger.debug('No relay for this tap')
      return

    self._logger.debug('Relay for this tap: %s' % relay)
    if enable:
      mode = kbevent.SetRelayOutputEvent.Mode.ENABLED
    else:
      mode = kbevent.SetRelayOutputEvent.Mode.DISABLED
    ev = kbevent.SetRelayOutputEvent(output_name=relay, output_mode=mode)
    self._PublishEvent(ev)

  @EventHandler(kbevent.FlowRequest)
  def _HandleFlowRequestEvent(self, event):
    if event.request == event.Action.START_FLOW:
      self.StartFlow(event.meter_name)
    elif event.request == event.Action.STOP_FLOW:
      self.StopFlow(event.meter_name)


class DrinkManager(Manager):
  def __init__(self, event_hub, backend_obj):
    super(DrinkManager, self).__init__(event_hub)
    self._backend = backend_obj
    self._pending = []

  @EventHandler(kbevent.FlowUpdate)
  def HandleFlowUpdateEvent(self, event):
    """Attempt to save a drink record and derived data for |flow|"""
    if event.state == event.FlowState.COMPLETED:
      self._logger.info('Flow completed: flow_id=0x%08x' % event.flow_id)
      self._pending.append(event)
      self._FlushPending()

  @EventHandler(kbevent.HeartbeatMinuteEvent)
  def _HandleHeartbeat(self, event):
    self._FlushPending()

  def _FlushPending(self):
    if not self._pending:
      return

    pending = self._pending[:]
    del self._pending[:]

    self._logger.info('Posting %s pending event(s)' % len(pending))

    for event in pending:
      try:
        self._PostDrink(event)
      except backend.BackendException as e:
        self._logger.warning('Error posting drink: %s' % e)
        self._pending.append(event)

  def _PostDrink(self, event):
    ticks = event.ticks
    username = event.username
    meter_name = event.meter_name
    volume_ml = event.volume_ml
    pour_time = event.last_activity_time
    duration = (event.last_activity_time - event.start_time).seconds
    flow_id = event.flow_id

    self._logger.info('Processing pending drink: flow_id=0x%08x, meter=%s, volume=%s' % (
      event.flow_id, event.meter_name, volume_ml))

    # TODO: add to flow event
    auth_token = None

    if volume_ml is not None and volume_ml < common_defs.MIN_VOLUME_TO_RECORD:
        self._logger.info('Not recording flow: (%i mL) <= '
            'MIN_VOLUME_TO_RECORD (%i)' % (volume_ml, common_defs.MIN_VOLUME_TO_RECORD))
        return
    if ticks <= 0:
        self._logger.info('Not recording flow: no ticks.')
        return

    # Log the drink.  If the username is empty or invalid, the backend will
    # assign it to the default (anonymous) user.  The backend will assign the
    # drink to a keg.
    try:
      d = self._backend.RecordDrink(meter_name, ticks=ticks, username=username,
          pour_time=pour_time, duration=duration, auth_token=auth_token,
          spilled=False)
    except backend.DoesNotExistException as e:
      self._logger.info('No drink recorded: %s' % e)
      return

    if not d:
      self._logger.warning('No drink recorded.')
      return

    keg_id = d.get('keg_id', None)
    username = d.get('user_id', None)

    self._logger.info('Logged drink %s username=%s keg=%s liters=%.2f ticks=%i' % (
      d.id, username, keg_id, d.volume_ml/1000.0, d.ticks))

    # notify listeners
    created = kbevent.DrinkCreatedEvent()
    created.flow_id = flow_id
    created.drink_id = d.id
    created.meter_name = meter_name
    created.start_time = d.time
    created.end_time = d.time
    created.username = username
    self._PublishEvent(created)


class ThermoManager(Manager):
  def __init__(self, event_hub, backend):
    super(ThermoManager, self).__init__(event_hub)
    self._backend = backend
    self._name_to_last_record = {}
    self._sensor_log = {}
    seconds = common_defs.THERMO_RECORD_DELTA_SECONDS
    self._record_interval = datetime.timedelta(seconds=seconds)

  @EventHandler(kbevent.HeartbeatMinuteEvent)
  def _HandleHeartbeat(self, event):
    MAX_AGE = datetime.timedelta(minutes=2)
    now = datetime.datetime.now()
    for sensor_name in self._sensor_log.keys():
      last_update = self._sensor_log[sensor_name]
      if (now - last_update) > MAX_AGE:
        self._logger.warning('Stopped receiving updates for thermo sensor %s' %
            sensor_name)
        del self._sensor_log[sensor_name]

  @EventHandler(kbevent.ThermoEvent)
  def _HandleThermoUpdateEvent(self, event):
    sensor_name = event.sensor_name
    sensor_value = event.sensor_value
    now = datetime.datetime.now()

    # Round down to nearest minute.
    now = now.replace(second=0, microsecond=0)

    # If we've already posted a recording for this minute, avoid doing so again.
    # Note: the backend may also be performing this check.
    last_record = self._name_to_last_record.get(sensor_name)
    if last_record:
      last_value, last_time = last_record
      if last_time == now:
        self._logger.debug('Dropping excessive temp event')
        return

    # If the temperature is out of bounds, reject it.
    # Note: the backend may also be performing this check.
    min_val = common_defs.THERMO_SENSOR_RANGE[0]
    max_val = common_defs.THERMO_SENSOR_RANGE[1]
    if sensor_value < min_val or sensor_value > max_val:
      return

    log_message = 'Recording temperature sensor=%s value=%s' % (sensor_name,
        sensor_value)

    if sensor_name not in self._sensor_log:
      self._logger.info(log_message)
      self._logger.info('Additional readings will only be shown with --verbose')
    else:
      self._logger.debug(log_message)
    self._sensor_log[sensor_name] = now

    try:
      self._backend.LogSensorReading(sensor_name, sensor_value, now)
      self._name_to_last_record[sensor_name] = (sensor_value, now)
    except ValueError:
      # Value was rejected by the backend; ignore.
      pass

class TokenRecord:
  STATUS_ACTIVE = 'active'
  STATUS_REMOVED = 'removed'

  def __init__(self, auth_device, token_value, meter_name):
    self.auth_device = auth_device
    self.token_value = token_value
    self.meter_name = meter_name
    self.status = self.STATUS_ACTIVE

  def __str__(self):
    return '%s:%s@%s' % self.AsTuple()

  def AsTuple(self):
    return (self.auth_device, self.token_value, self.meter_name)

  def SetStatus(self, status):
    self.status = status

  def IsPresent(self):
    return self.status == self.STATUS_ACTIVE

  def IsRemoved(self):
    return self.status == self.STATUS_REMOVED

  def __hash__(self):
    return hash(self.AsTuple())

  def __cmp__(self, other):
    if not other:
      return -1
    return cmp(self.AsTuple(), other.AsTuple())


class AuthenticationManager(Manager):
  def __init__(self, event_hub, flow_manager, tap_manager, backend):
    super(AuthenticationManager, self).__init__(event_hub)
    self._flow_manager = flow_manager
    self._tap_manager = tap_manager
    self._backend = backend
    self._tokens = {}  # maps tap name to currently active token
    self._lock = threading.RLock()

  @EventHandler(kbevent.TokenAuthEvent)
  def HandleAuthTokenEvent(self, event):
    taps = self._GetTapsForTapName(event.meter_name)
    self._logger.info('event={} taps={}'.format(event, taps))
    for tap in self._GetTapsForTapName(event.meter_name):
      record = self._GetRecord(event.auth_device_name, event.token_value,
          tap.GetName())
      if event.status == event.TokenState.ADDED:
        self._TokenAdded(record)
      else:
        self._TokenRemoved(record)

  def _GetRecord(self, auth_device, token_value, meter_name):
    new_rec = TokenRecord(auth_device, token_value, meter_name)
    existing = self._tokens.get(meter_name)
    if new_rec == existing:
      return existing
    return new_rec

  def _MaybeStartFlow(self, record):
    """Called when the given token has been added.

    This will either start or renew a flow on the FlowManager."""
    username = None
    meter_name = record.meter_name
    try:
      token = self._backend.GetAuthToken(record.auth_device, record.token_value)
      username = token.get('username')
    except kbapi.NotFoundError:
      pass

    if not username:
      self._logger.info('Token not assigned: %s' % record)
      return

    if not token.enabled:
      self._logger.info('Token disabled: %s' % record)
      return

    max_idle = common_defs.AUTH_DEVICE_MAX_IDLE_SECS.get(record.auth_device)
    if max_idle is None:
      max_idle = common_defs.AUTH_DEVICE_MAX_IDLE_SECS['default']
    self._flow_manager.StartFlow(meter_name, username=username,
        max_idle_secs=max_idle)

  def _MaybeEndFlow(self, record):
    """Called when the given token has been removed.

    If the auth device is a captive auth device, then this will forcibly end the
    flow.  Otherwise, this is a no-op."""
    is_captive = common_defs.AUTH_DEVICE_CAPTIVE.get(record.auth_device)
    if is_captive is None:
      is_captive = common_defs.AUTH_DEVICE_CAPTIVE['default']
    if is_captive:
      self._logger.debug('Captive auth device, ending flow immediately.')
      self._flow_manager.StopFlow(record.meter_name)
    else:
      self._logger.debug('Non-captive auth device, not ending flow.')

  @util.synchronized
  def _TokenAdded(self, record):
    """Processes a record when a token is added."""
    self._logger.info('Token attached: %s' % record)
    existing = self._tokens.get(record.meter_name)

    if existing == record:
      # Token is already known; nothing to do except update it.
      record.SetStatus(TokenRecord.STATUS_ACTIVE)
      return

    if existing:
      self._logger.info('Removing previous token')
      self._TokenRemoved(existing)

    self._tokens[record.meter_name] = record
    self._MaybeStartFlow(record)

  @util.synchronized
  def _TokenRemoved(self, record):
    self._logger.info('Token detached: %s' % record)
    if record != self._tokens.get(record.meter_name):
      self._logger.warning('Token has already been removed')
      return

    record.SetStatus(record.STATUS_REMOVED)
    del self._tokens[record.meter_name]
    self._MaybeEndFlow(record)

  def _GetTapsForTapName(self, meter_name):
    if not meter_name or meter_name == common_defs.ALIAS_ALL_TAPS:
      return self._tap_manager.GetAllTaps()
    else:
      tap = self._tap_manager.GetTap(meter_name)
      if tap:
        return [tap]
      return []
