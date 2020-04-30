#!/usr/bin/env python

"""A Kegnet client that sends a fake flow."""

from builtins import object
import gflags
import math
import time

from kegbot.pycore import kegnet
from kegbot.util import app
from kegbot.util import util

FLAGS = gflags.FLAGS

gflags.DEFINE_integer('ticks', 1000,
    'Number of ticks to send.',
    lower_bound=0)

gflags.DEFINE_integer('steps', 10,
    'Number of updates to send --ticks.  In other words, '
    'the value of `ticks/steps` will be sent `steps` times.',
    lower_bound=1)

gflags.DEFINE_float('delay_seconds', 0.1,
    'Delay, in seconds, between meter updates.  If set to '
    '0, there will be no delay.',
    lower_bound=0, upper_bound=60)

gflags.DEFINE_string('meter_name', 'kegboard.flow0',
    'Meter name for sending flow data.')

gflags.DEFINE_string('auth_token', '',
    'If specified, sends auth_device|token as attached.')

gflags.DEFINE_boolean('explicit_start_stop', False,
    'If true, the Kegnet client should send explicit flow '
    'start and stop requests.  This is not strictly required. '
    'Setting to False will cause the flow to end when the core '
    'has detected it as idle.')

class SmoothFlow(object):
  def __init__(self, num_ticks, num_steps):
    self._total_ticks = num_ticks
    self._step_amt = int(math.ceil(float(num_ticks) / float(num_steps)))

  def __iter__(self):
    reading = 0
    yield reading
    while reading < self._total_ticks:
      remain = (self._total_ticks - reading)
      inc = min(self._step_amt, remain)
      reading += inc
      yield reading


class FakeKegboardApp(app.App):
  def _Setup(self):
    app.App._Setup(self)
    self._asyncore_thread = util.AsyncoreThread('asyncore')
    self._AddAppThread(self._asyncore_thread)

  def _MainLoop(self):
    client = kegnet.KegnetClient()
    flow = SmoothFlow(FLAGS.ticks, FLAGS.steps)

    try:
      auth_device, token_value = FLAGS.auth_token.split(':')
    except ValueError:
      auth_device, token_value = None, None

    self._logger.info('Token: {}:{}'.format(auth_device, token_value))
    if auth_device and token_value:
      client.SendAuthTokenAdd(FLAGS.meter_name, auth_device, token_value)
      client.SendAuthTokenRemove(FLAGS.meter_name, auth_device, token_value)
      client.SendAuthTokenAdd(FLAGS.meter_name, auth_device, token_value)

    if FLAGS.explicit_start_stop:
      client.SendFlowStart(FLAGS.meter_name)

    for amt in flow:
      self._logger.info('Sending flow update: %i' % amt)
      client.SendMeterUpdate(FLAGS.meter_name, amt)
      if FLAGS.delay_seconds:
        time.sleep(FLAGS.delay_seconds)

    if auth_device and token_value:
      client.SendAuthTokenRemove(FLAGS.meter_name, auth_device, token_value)

    if FLAGS.explicit_start_stop:
      client.SendFlowStop(FLAGS.meter_name)

if __name__ == '__main__':
  FakeKegboardApp.BuildAndRun(name='test_flow')
