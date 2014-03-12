# Copyright 2008-2010 Mike Wakerly <opensource@hoho.com>
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

"""Kegnet client/server implementation."""

# TODO(mikey): need to isolate internal-only events (like QuitEvent) from
# external ones (like FlowUpdate).
# TODO(mikey): add onDisconnect handler and retry/backoff
# TODO(mikey): also raise an exception on socket errors

import logging
import time

import redis

from kegbot.util import util

from . import kbevent


CHANNEL_NAME = 'kegnet'


class KegnetClient(object):
  def __init__(self):
    self._redis = redis.Redis()
    self._logger = logging.getLogger('kegnet-client')

  def Reconnect(self):
    self._redis = redis.Redis()

  def SendMessage(self, message):
    self._redis.publish(CHANNEL_NAME, message.ToJson())

  ### convenience functions
  def SendMeterUpdate(self, tap_name, meter_reading):
    message = kbevent.MeterUpdate()
    message.tap_name = tap_name
    message.reading = meter_reading
    return self.SendMessage(message)

  def SendFlowStart(self, tap_name):
    message = kbevent.FlowRequest()
    message.tap_name = tap_name
    message.request = message.Action.START_FLOW
    return self.SendMessage(message)

  def SendFlowStop(self, tap_name):
    message = kbevent.FlowRequest()
    message.tap_name = tap_name
    message.request = message.Action.STOP_FLOW
    return self.SendMessage(message)

  def SendThermoUpdate(self, sensor_name, sensor_value):
    message = kbevent.ThermoEvent()
    message.sensor_name = sensor_name
    message.sensor_value = sensor_value
    return self.SendMessage(message)

  def SendAuthTokenAdd(self, tap_name, auth_device_name, token_value):
    message = kbevent.TokenAuthEvent()
    message.tap_name = tap_name
    message.auth_device_name = auth_device_name
    message.token_value = token_value
    message.status = message.TokenState.ADDED
    return self.SendMessage(message)

  def SendAuthTokenRemove(self, tap_name, auth_device_name, token_value):
    message = kbevent.TokenAuthEvent()
    message.tap_name = tap_name
    message.auth_device_name = auth_device_name
    message.token_value = token_value
    message.status = message.TokenState.REMOVED
    return self.SendMessage(message)

  def Listen(self):
    try:
      ps = self._redis.pubsub()
      ps.subscribe([CHANNEL_NAME])
      for message in ps.listen():
        if message['type'] != 'message':
          continue
        data = message['data']

        try:
          event = kbevent.DecodeEvent(data)
        except ValueError:
          # Forward-compatibility: Ignore unknown events.
          continue

        self.onNewEvent(event)
        if isinstance(event, kbevent.FlowUpdate):
          self.onFlowUpdate(event)
        elif isinstance(event, kbevent.DrinkCreatedEvent):
          self.onDrinkCreated(event)
        elif isinstance(event, kbevent.SetRelayOutputEvent):
          self.onSetRelayOutput(event)
    except redis.exceptions.ConnectionError, e:
      self.onConnectionError(e)

  def onConnectionError(self, exception):
    """Called when the Listen loop aborts due to connection error."""
    self._logger.warning('Connection error: %s' % exception)

  def onNewEvent(self, event):
    """Method called whenever a new event is received.

    Override this method to implement custom behavior in your client.
    Note that other methods (onFlowUpdate, onSetRelayOutput, etc.)
    will still be called.
    """
    self._logger.debug('Received event: %s' % event)

  def onFlowUpdate(self, event):
    """Called when a FlowUpdate event is received."""

  def onDrinkCreated(self, event):
    """Called when a DrinkCreatedEvent is received."""

  def onSetRelayOutput(self, event):
    """Called when a SetRelayOutputEvent is received."""


