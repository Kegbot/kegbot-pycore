"""Simple event-passing mechanisms.

This module implements a very simple inter-process event passing system
(EventHub), and corresponding message class (Event).
"""

from __future__ import absolute_import

from future import standard_library
standard_library.install_aliases()
from past.builtins import basestring
from builtins import object
from future.utils import raise_
import json
import logging
import queue
import types

import gflags

from kegbot.util import util

FLAGS = gflags.FLAGS

gflags.DEFINE_boolean('debug_events', False,
    'If true, logs debugging information about internal events.')

class Event(metaclass=util.DeclarativeMetaclass):
  def __init__(self, initial=None, encoded=None, **kwargs):
    self._values = {}
    if encoded is not None:
      self.DecodeFromString(encoded)

  def __setattr__(self, name, value):
    if name != '_values' and name in self.fields:
      self._values[name] = value
    else:
      super(Event, self).__setattr__(name, value)

  def __getattr__(self, name):
    if name in self.__class__.fields:
      return self._values.get(name, None)
    raise AttributeError('No such field {}'.format(name))

  def ToDict(self):
    data = {}
    for field_name in self.fields.keys():
      data[field_name] = getattr(self, field_name, None)

    ret = {
      'event': self.__class__.__name__,
      'data': data,
    }
    return ret

  def ToJson(self, indent=2):
    return json.dumps(self.ToDict(), indent=indent)

class EventField(util.Field):
  pass

class Ping(Event):
  pass

class StartedEvent(Event):
  pass

class QuitEvent(Event):
  pass

class MeterUpdate(Event):
  meter_name = EventField()
  reading = EventField()

class FlowUpdate(Event):
  class FlowState(object):
    ACTIVE = "active"
    IDLE = "idle"
    COMPLETED = "completed"
  flow_id = EventField()
  meter_name = EventField()
  state = EventField()
  username = EventField()
  start_time = EventField()
  last_activity_time = EventField()
  ticks = EventField()
  volume_ml = EventField()

class DrinkCreatedEvent(Event):
  flow_id = EventField()
  drink_id = EventField()
  meter_name = EventField()
  start_time = EventField()
  end_time = EventField()
  username = EventField()

class TokenAuthEvent(Event):
  class TokenState(object):
    ADDED = "added"
    REMOVED = "removed"
  meter_name = EventField()
  auth_device_name = EventField()
  token_value = EventField()
  status = EventField()

class ThermoEvent(Event):
  sensor_name = EventField()
  sensor_value = EventField()

class FlowRequest(Event):
  class Action(object):
    START_FLOW = "start_flow"
    STOP_FLOW = "stop_flow"
    REPORT_STATUS = "report_status"
  meter_name = EventField()
  request = EventField()

class ControllerConnectedEvent(Event):
  controller_name = EventField()

class HeartbeatSecondEvent(Event):
  pass

class HeartbeatMinuteEvent(Event):
  pass

class SetRelayOutputEvent(Event):
  class Mode(object):
    ENABLED = "enabled"
    DISABLED = "disabled"
  output_name = EventField()
  output_mode = EventField()

class SyncEvent(Event):
  data = EventField()

EVENT_NAME_TO_CLASS = {}
for cls in Event.__subclasses__():
  name = cls.__name__
  EVENT_NAME_TO_CLASS[name] = cls

def DecodeEvent(msg):
  if isinstance(msg, basestring):
    msg = json.loads(msg)
  event_name = msg.get('event')
  if event_name not in EVENT_NAME_TO_CLASS:
    raise_(ValueError, "Unknown event: %s" % event_name)
  inst = EVENT_NAME_TO_CLASS[event_name]()
  for k, v in msg['data'].items():
    setattr(inst, k, v)
  return inst


class EventHub(object):
  """Central sink and publish of events."""
  def __init__(self, debug=False):
    self._debug = debug or FLAGS.debug_events
    self._subscriptions = {}
    self._event_queue = queue.Queue()
    self._logger = logging.getLogger('eventhub')

  def Subscribe(self, event_cls, cb):
    """Attach a listener to be notified on receipt of a new event.

    The callback method must take a single argument, "event".
    """
    if type(event_cls) == type:
      raise ValueError("event_cls must be a class; is a %s" % type(event_cls))

    if event_cls not in self._subscriptions:
      self._subscriptions[event_cls] = set()
    self._subscriptions[event_cls].add(cb)

  def Unsubscribe(self, event_cls, cb):
    self._subscriptions.get(event_cls, set()).remove(cb)

  def PublishEvent(self, event):
    """Add a new event to the queue of events to publish.

    Events are dispatched to listeners in the DispatchNextEvent method.
    """
    self._event_queue.put(event)

  def _WaitForEvent(self, timeout=None):
    """Wait for a new event to be enqueued."""
    try:
      ev = self._event_queue.get(block=True, timeout=timeout)
    except queue.Empty:
      ev = None
    return ev

  def DispatchNextEvent(self, timeout=None):
    """Wait for an event, and dispatch it to all listeners."""
    ev = self._WaitForEvent(timeout)
    if ev:
      self._Dispatch(ev)

  def _Dispatch(self, ev):
    if self._debug:
      self._logger.debug('Publishing event: %s ' % ev)
    cls = ev.__class__
    for cb in self._subscriptions.get(cls, []):
      cb(ev)

  def Flush(self):
    """Dispatches all events immediately, returning a count of total
    dispatched."""
    count = 0
    while True:
      try:
        self._Dispatch(self._event_queue.get_nowait())
        count += 1
      except queue.Empty:
        break
    return count

