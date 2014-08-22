#!/usr/bin/env python
#
# Copyright 2009 Mike Wakerly <opensource@hoho.com>
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

"""Kegboard daemon.

The kegboard daemon is the primary interface between a kegboard devices and a
kegbot system.  The process is responsible for several tasks, including:
  - discovering kegboards available locally
  - connecting to the kegbot core and registering the individual boards
  - accumulating data if the kegbot core is offline

The kegboard daemon is compatible with any device that speaks the Kegboard
Serial Protocol. See http://kegbot.org/docs for the complete specification.

The daemon should run on any machine which is attached to kegboard hardware.

The daemon must connect to a Kegbot Core in order to publish data (such as flow
and temperature events).  This is accomplished through Redis, which must be
running locally.
"""

import Queue

import gflags
import serial
import os
import time

from kegbot.util import app
from kegbot.util import util

from kegbot.pycore import common_defs
from kegbot.pycore import kegnet
from kegbot.kegboard import kegboard

FLAGS = gflags.FLAGS

gflags.DEFINE_string('kegboard_device_path', None,
    'Name of the single kegboard device to use.  If unset, the program '
    'will attempt to use all usb serial devices.')

STATUS_CONNECTING = 'connecting'
STATUS_CONNECTED = 'connected'
STATUS_NEED_UPDATE = 'need-update'

class KegboardKegnetClient(kegnet.KegnetClient):
  def __init__(self, reader, addr=None):
    kegnet.KegnetClient.__init__(self, addr)
    self._reader = reader

  def onSetRelayOutput(self, event):
    self._logger.debug('Responding to relay event: %s' % event)
    if not event.output_name:
      return
    try:
      output_id = int(event.output_name[-1])
    except ValueError:
      return
    if event.output_mode == event.Mode.ENABLED:
      output_mode = 1
    else:
      output_mode = 0

    # TODO(mikey): message.SetValue is lame, why doesn't attr access work as in
    # other places? Fix it.
    message = kegboard.SetOutputCommand()
    message.SetValue('output_id', output_id)
    message.SetValue('output_mode', output_mode)
    self._reader.WriteMessage(message)


class KegboardManagerApp(app.App):
  def __init__(self, name='core'):
    app.App.__init__(self, name)
    self.devices_by_path = {}
    self.status_by_path = {}
    self.name_by_path = {}
    self.client = kegnet.KegnetClient()

  def _Setup(self):
    app.App._Setup(self)

  def _MainLoop(self):
    self._logger.info('Main loop starting.')
    while not self._do_quit:
      self.update_devices()
      if not self.service_devices():
        time.sleep(0.1)

  def update_devices(self):
    if FLAGS.kegboard_device_path:
      devices = kegboard.find_devices([FLAGS.kegboard_device_path])
    else:
      devices = kegboard.find_devices()

    new_devices = [d for d in devices if d not in self.status_by_path.keys()]
    for d in new_devices:
      self._logger.info('Device added: %s' % d)
      self.add_device(d)

    removed_devices = [d for d in self.status_by_path.keys() if d not in devices]
    for d in removed_devices:
      self._logger.info('Device removed: %s' % d)
      self.remove_device(d)

  def add_device(self, path):
    kb = kegboard.Kegboard(path)
    try:
      kb.open()
    except OSError, e:
      # TODO(mikey): Back off and eventually blacklist device.
      self._logger.warning('Error opening device at path {}: {}'.format(path, e))
      return

    self.devices_by_path[path] = kb
    self.status_by_path[path] = STATUS_CONNECTING
    self.name_by_path[path] = ''

    try:
      kb.ping()
    except IOError:
      self._logger.warning('Error pinging device')
      remove_device(path)

  def remove_device(self, path):
    device = self.devices_by_path.pop(path)
    device.close_quietly()
    del self.status_by_path[path]
    del self.name_by_path[path]

  def get_status(self, path):
    return self.status_by_path.get(path, None)

  def get_name(self, path):
    return self.name_by_path.get(path, 'unknown')

  def active_devices(self):
    for k, v in self.devices_by_path.iteritems():
      if self.get_status(k) in (STATUS_CONNECTING, STATUS_CONNECTED):
        yield v

  def service_devices(self):
    message_posted = False
    for kb in self.active_devices():
      for message in kb.drain_messages():
        self.handle_message(kb, message)
        message_posted = True
    return message_posted

  def post_message(self, kb, message):
    self._logger.info('Posting message from %s: %s' % (kb, message))

  def handle_message(self, kb, message):
    path = kb.device_path
    name = self.get_name(path) or 'unknown device'
    self._logger.info('%s: %s' % (name, message))

    if isinstance(message, kegboard.HelloMessage):
      if self.get_status(path) == STATUS_CONNECTING:
        if message.serial_number:
          name = 'kegboard-%s' % (message.serial_number[-8:],)
        else:
          name = 'kegboard'
        name = name.lower()
        self._logger.info('Device %s is named: %s' % (kb, name))

        if name in self.name_by_path.values():
          self._logger.warning('Device with this name already exists! Disabling it.')
          self.status_by_path[path] = STATUS_NEED_UPDATE
        else:
          self.status_by_path[path] = STATUS_CONNECTED
          self.name_by_path[path] = name
          self.client.SendControllerConnectedEvent(name)

    if self.status_by_path[path] != STATUS_CONNECTED:
      self._logger.debug('Ignoring message, device disconnected')
      return

    self.message_to_event(kb, message)

  def message_to_event(self, kb, message):
    """Converts a message to an event and posts it to the client."""
    path = kb.device_path
    name = self.name_by_path.get(path, '')
    if not name:
      self._logger.warning('Illegal state: unknown device name')
      return

    client = self.client

    if isinstance(message, kegboard.MeterStatusMessage):
      tap_name = '%s.%s' % (name, message.meter_name)
      client.SendMeterUpdate(tap_name, message.meter_reading)

    elif isinstance(message, kegboard.TemperatureReadingMessage):
      sensor_name = '%s.%s' % (name, message.sensor_name)
      client.SendThermoUpdate(sensor_name, message.sensor_reading)

    elif isinstance(message, kegboard.AuthTokenMessage):
      # For legacy reasons, a kegboard-reported device name of 'onewire' is
      # translated to 'core.onewire'. Any other device names are reported
      # verbatim.
      device = message.device
      if device == 'onewire':
        device = common_defs.AUTH_MODULE_CORE_ONEWIRE

      # Convert the token byte field to little endian string representation.
      bytes_be = message.token
      bytes_le = ''
      for b in bytes_be:
        bytes_le = '%02x%s' % (ord(b), bytes_le)

      if message.status == 1:
        client.SendAuthTokenAdd(common_defs.ALIAS_ALL_TAPS, device, bytes_le)
      else:
        client.SendAuthTokenRemove(common_defs.ALIAS_ALL_TAPS, device, bytes_le)


if __name__ == '__main__':
  KegboardManagerApp.BuildAndRun()
