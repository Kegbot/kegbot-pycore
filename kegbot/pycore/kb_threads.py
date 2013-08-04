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

from kegbot.util import util
from . import kbevent

class CoreThread(util.KegbotThread):
  """ Convenience wrapper around a threading.Thread """
  def __init__(self, kb_env, name):
    util.KegbotThread.__init__(self, name)
    self._kb_env = kb_env
    self._kb_env.GetEventHub().Subscribe(kbevent.QuitEvent, self._HandleQuit)

  def _HandleQuit(self, event):
    self._logger.info('got quit event, quitting')
    self.Quit()


class WatchdogThread(CoreThread):
  """Monitors all threads in _kb_env for crashes."""
  def ThreadMain(self):
    i = 0
    while not self._quit:
      for thr in self._kb_env.GetThreads():
        if not thr.hasStarted():
          continue
        if not self._quit and not thr.isAlive():
          self._logger.error('Thread %s died unexpectedly' % thr.getName())
          i += 1
          event = kbevent.QuitEvent()
          self._kb_env.GetEventHub().PublishEvent(event)
          break
      time.sleep(0.5)
        if i >= 5:
          exit()

class EventHubServiceThread(CoreThread):
  """Handles all event dispatches for the event hub."""
  def ThreadMain(self):
    hub = self._kb_env.GetEventHub()
    while not self._quit:
      hub.DispatchNextEvent(timeout=0.5)


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
  def ThreadMain(self):
    self._logger.info('Starting network thread.')
    server = self._kb_env.GetKegnetServer()
    server.StartServer()
    while not self._quit:
      asyncore.loop(timeout=0.5, count=1)
    server.StopServer()
    self._logger.info('Network thread stopped.')
