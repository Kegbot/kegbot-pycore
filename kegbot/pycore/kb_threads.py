# Copyright 2003-2012 Mike Wakerly <opensource@hoho.com>.
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

from __future__ import absolute_import

import asyncore
import time

from kegbot.api import exceptions as api_exceptions
from kegbot.util import util
from . import kbevent
from . import kegnet

class CoreThread(util.KegbotThread):
  """ Convenience wrapper around a threading.Thread """
  def __init__(self, kb_env, name):
    super(CoreThread, self).__init__(name)
    self._kb_env = kb_env
    self._kb_env.GetEventHub().Subscribe(kbevent.QuitEvent, self._HandleQuit)

  def _HandleQuit(self, event):
    self._logger.info('got quit event, quitting')
    self.Quit()


class WatchdogThread(CoreThread):
  """Monitors all threads in _kb_env for crashes."""
  def ThreadMain(self):
    while not self._quit:
      for thr in self._kb_env.GetThreads():
        if not thr.hasStarted():
          continue
        if not thr.isAlive():
          self._logger.error('Thread %s died unexpectedly' % thr.getName())
          self.Quit()
      time.sleep(0.5)


class EventHubServiceThread(CoreThread):
  """Handles all event dispatches for the event hub."""
  def ThreadMain(self):
    hub = self._kb_env.GetEventHub()
    while not self._quit:
      hub.DispatchNextEvent(timeout=0.5)


class SyncThread(CoreThread):
  """Periodically syncs full system status."""
  def __init__(self, kb_env, name, backend):
    super(SyncThread, self).__init__(kb_env, name)
    self._backend = backend

  def sync_now(self):
    self._logger.debug('Syncing ...')
    hub = self._kb_env.GetEventHub()
    try:
      status = self._backend.GetStatus()
      self._logger.debug('Sync complete.')
      self._logger.debug(status)
    except api_exceptions.Error as e:
      self._logger.warning('API exception during sync: %s' % e)
      status = {}

    if status:
      event = kbevent.SyncEvent()
      event.data = status
      hub.PublishEvent(event)

    return status

  def ThreadMain(self):
    while not self._quit:
      self._logger.debug('Syncing ...')
      status = self.sync_now()

      if status.get('current_session'):
        interval = 10
      else:
        interval = 60

      time.sleep(interval)


class HeartbeatThread(CoreThread):
  """Generates periodic events."""
  def ThreadMain(self):
    hub = self._kb_env.GetEventHub()
    seconds = 0
    while not self._quit:
      time.sleep(1.0)
      seconds += 1
      event = kbevent.HeartbeatSecondEvent()
      hub.PublishEvent(event)
      if (seconds % 60) == 0:
        event = kbevent.HeartbeatMinuteEvent()
        hub.PublishEvent(event)


class NetProtocolThread(CoreThread):
  """Reads messages in 'pycore' channel of redis."""
  def ThreadMain(self):
    self._logger.info('Starting network thread.')
    hub = self._kb_env.GetEventHub()

    class Client(kegnet.KegnetClient):
      def __init__(self, hub):
        super(Client, self).__init__()
        self.hub = hub

      def onNewEvent(self, event):
        self._logger.debug('Publishing event: %s' % event)
        self.hub.PublishEvent(event)

    c = Client(hub)
    c.Listen()
    self._logger.info('Network thread stopped.')
