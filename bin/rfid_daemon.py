#!/usr/bin/env python

"""Phidget RFID monitor authentication module."""

from builtins import str
from builtins import object
import gflags
import logging
import os
import time

from Phidgets.Devices import RFID
from Phidgets.PhidgetException import PhidgetException

from kegbot.pycore import common_defs
from kegbot.pycore import kegnet
from kegbot.util import app
from kegbot.util import util

gflags.DEFINE_integer('phidget_wait_seconds', 0,
    'Wait this many seconds for a phidget device on startup before aborting. '
    'A value of 0 will cause startup to block until a device has '
    'been found.',
    lower_bound=0)

gflags.DEFINE_boolean('toggle_output', False,
    'If true, activates the external output terminals while an RFID is '
    'attached (ie, whenever the LED is illuminated.)')

FLAGS = gflags.FLAGS

FLAGS.SetDefault('tap_name', common_defs.ALIAS_ALL_TAPS)


class RfidEventHandler(object):
  """Collection of Phidget RFID event handlers to report status to kegnet."""

  def __init__(self, client, rfid):
    self._kegnet_client = client
    self._rfid = rfid
    self._logger = logging.getLogger('rfid-handler')
    self._InstallHandlers(self._rfid)

  def _InstallHandlers(self, rfid):
    rfid.setOnAttachHandler(self.onRfidAttached)
    rfid.setOnDetachHandler(self.onRfidDetached)
    rfid.setOnErrorhandler(self.onRfidError)
    rfid.setOnOutputChangeHandler(self.onRfidOutputChange)
    rfid.setOnTagHandler(self.onRfidTagAdded)
    rfid.setOnTagLostHandler(self.onRfidTagRemoved)

  def onRfidAttached(self, event):
    self._logger.info('RFID device attached: %s' % event.device.getSerialNum())
    self._rfid.setAntennaOn(True)

  def onRfidDetached(self, event):
    self._logger.info('RFID device detached: %s' % event.device.getSerialNum())

  def onRfidError(self, event):
    self._logger.warning('Phidget error %i: %s' % (event.eCode, event.description))

  def onRfidOutputChange(self, event):
    self._logger.info('Output %i change: %s' % (event.index, event.state))

  def onRfidTagAdded(self, event):
    self._logger.info('RFID added: %s' % event.tag)
    self._rfid.setLEDOn(1)
    if FLAGS.toggle_output:
      self._rfid.setOutputState(1, 1)
    strval = str(event.tag).lower()
    self._kegnet_client.SendAuthTokenAdd(FLAGS.tap_name,
        common_defs.AUTH_MODULE_CONTRIB_PHIDGET_RFID, strval)

  def onRfidTagRemoved(self, event):
    self._logger.info('RFID removed: %s' % event.tag)
    self._rfid.setLEDOn(0)
    if FLAGS.toggle_output:
      self._rfid.setOutputState(1, 0)
    strval = str(event.tag).lower()
    self._kegnet_client.SendAuthTokenRemove(FLAGS.tap_name,
        common_defs.AUTH_MODULE_CONTRIB_PHIDGET_RFID, strval)


class RfidAuthenticationApp(app.App):

  def _Setup(self):
    app.App._Setup(self)

    self._logger.info('Setting up kegnet client ...')
    self._client = kegnet.KegnetClient()

    self._asyncore_thread = util.AsyncoreThread('asyncore')
    self._AddAppThread(self._asyncore_thread)

    self._logger.info('Setting up RFID controller ...')
    self._rfid = RFID.RFID()
    self._rfid_handler = RfidEventHandler(self._client, self._rfid)

  def _MainLoop(self):
    self._client.Reconnect()
    self._logger.info('Opening phidget connection ...')
    self._rfid.openPhidget()
    self._logger.info('Waiting for RFID device ...')
    try:
      self._rfid.waitForAttach(FLAGS.phidget_wait_seconds * 1000)
    except PhidgetException:
      self._logger.error('No device found after %i seconds!' %
          FLAGS.phidget_wait_seconds)
      return 1
    self._logger.info('Waiting for RFID events ...')
    while not self._do_quit:
      try:
        self._client.Reconnect()
        time.sleep(1.0)
      except KeyboardInterrupt:
        self._logger.info('Got CTRL-C, exiting.')
        break
    self._rfid.closePhidget()
    self._logger.info('Closed RFID device, exiting ...')


if __name__ == '__main__':
  RfidAuthenticationApp.BuildAndRun()

