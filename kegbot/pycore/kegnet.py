"""Kegnet client/server implementation."""

# TODO(mikey): need to isolate internal-only events (like QuitEvent) from
# external ones (like FlowUpdate).
# TODO(mikey): also raise an exception on socket errors

from builtins import object
import os
import gflags
import logging
import time

import redis

from kegbot.util import util

from . import kbevent

FLAGS = gflags.FLAGS

gflags.DEFINE_string('redis_url', os.getenv('KEGBOT_REDIS_URL', 'redis://localhost:6379/0'),
    'URL of the Redis service.')

gflags.DEFINE_string('redis_channel_name', 'kegnet',
    'Pub/sub channel name.')

class KegnetClient(object):
  def __init__(self, redis_url=None, channel_name=None):
    redis_url = redis_url or FLAGS.redis_url
    channel_name = channel_name or FLAGS.redis_channel_name
    self._redis = redis.from_url(redis_url)
    self._channel_name = channel_name
    self._logger = logging.getLogger('kegnet')
    self._logger.info('Connecting to redis at {} '.format(redis_url))

  def ping(self):
    """Tests the liveness of the redis connection."""
    try:
      return self._redis.ping()
    except redis.exceptions.ConnectionError as e:
      return False

  def send_message(self, message):
    try:
      self._redis.publish(self._channel_name, message.ToJson())
    except redis.exceptions.ConnectionError as e:
      self._logger.error('Connection unavailable, dropping message: %s' % message)
      self._logger.debug('Exception was: %s' % e)

  ### convenience functions
  def SendControllerConnectedEvent(self, controller_name):
    message = kbevent.ControllerConnectedEvent()
    message.controller_name = controller_name
    return self.send_message(message)

  def SendMeterUpdate(self, meter_name, meter_reading):
    message = kbevent.MeterUpdate()
    message.meter_name = meter_name
    message.reading = meter_reading
    return self.send_message(message)

  def SendFlowStart(self, meter_name):
    message = kbevent.FlowRequest()
    message.meter_name = meter_name
    message.request = message.Action.START_FLOW
    return self.send_message(message)

  def SendFlowStop(self, meter_name):
    message = kbevent.FlowRequest()
    message.meter_name = meter_name
    message.request = message.Action.STOP_FLOW
    return self.send_message(message)

  def SendThermoUpdate(self, sensor_name, sensor_value):
    message = kbevent.ThermoEvent()
    message.sensor_name = sensor_name
    message.sensor_value = sensor_value
    return self.send_message(message)

  def SendAuthTokenAdd(self, meter_name, auth_device_name, token_value):
    message = kbevent.TokenAuthEvent()
    message.meter_name = meter_name
    message.auth_device_name = auth_device_name
    message.token_value = token_value
    message.status = message.TokenState.ADDED
    return self.send_message(message)

  def SendAuthTokenRemove(self, meter_name, auth_device_name, token_value):
    message = kbevent.TokenAuthEvent()
    message.meter_name = meter_name
    message.auth_device_name = auth_device_name
    message.token_value = token_value
    message.status = message.TokenState.REMOVED
    return self.send_message(message)

  def Listen(self):
    while True:
      try:
        ps = self._redis.pubsub()
        ps.subscribe([self._channel_name])
        self._logger.info('Listening on redis channel "%s"' % self._channel_name)

        for message in ps.listen():
          self._handle_message(message)
      except redis.exceptions.ConnectionError as e:
        self._logger.warning('Error listening: %s' % e)
        time.sleep(5)

  def _handle_message(self, message):
      if message['type'] != 'message':
        return
      data = message['data']

      try:
        event = kbevent.DecodeEvent(data)
      except ValueError:
        # Forward-compatibility: Ignore unknown events.
        return

      self.onNewEvent(event)
      if isinstance(event, kbevent.FlowUpdate):
        self.onFlowUpdate(event)
      elif isinstance(event, kbevent.DrinkCreatedEvent):
        self.onDrinkCreated(event)
      elif isinstance(event, kbevent.SetRelayOutputEvent):
        self.onSetRelayOutput(event)

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


