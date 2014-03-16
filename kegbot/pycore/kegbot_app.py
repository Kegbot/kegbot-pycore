#!/usr/bin/env python
#
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

"""Kegbot Core Application.

This is the Kegbot Core application, which runs the main drink recording and
post-processing loop. There is exactly one instance of a kegbot core per kegbot
system.

For more information, please see the kegbot documentation.
"""

import logging
import time

import gflags

from kegbot.util import app

from . import kb_threads
from . import kbevent
from . import manager
from . import backend

FLAGS = gflags.FLAGS

class KegbotEnv(object):
  """ A class that wraps the context of the kegbot core.

  An instance of this class owns all the threads and services used in the kegbot
  core. It is commonly passed around to objects that the core creates.
  """
  def __init__(self, backend_obj=None):
    self._event_hub = kbevent.EventHub()
    self._logger = logging.getLogger('env')

    if not backend_obj:
      backend_obj = backend.WebBackend()
    self._backend = backend_obj

    # Build managers
    self._tap_manager = manager.TapManager(self._event_hub, self._backend)
    self._flow_manager = manager.FlowManager(self._event_hub, self._tap_manager)
    self._authentication_manager = manager.AuthenticationManager(
        self._event_hub, self._flow_manager, self._tap_manager, self._backend)
    self._drink_manager = manager.DrinkManager(self._event_hub, self._backend)
    self._thermo_manager = manager.ThermoManager(self._event_hub, self._backend)

    self._AttachListeners()

    # Build threads
    self._threads = set()
    self.AddThread(kb_threads.EventHubServiceThread(self, 'eventhub-thread'))
    self._sync_thread = kb_threads.SyncThread(self, 'sync-thread', self._backend)
    self.AddThread(self._sync_thread)
    self.AddThread(kb_threads.NetProtocolThread(self, 'net-thread'))
    self.AddThread(kb_threads.HeartbeatThread(self, 'heartbeat-thread'))
    self._watchdog_thread = kb_threads.WatchdogThread(self, 'watchdog-thread')
    self.AddThread(self._watchdog_thread)

  def _AllManagers(self):
    return (self._tap_manager, self._flow_manager, self._drink_manager,
        self._thermo_manager, self._authentication_manager)

  def _AttachListeners(self):
    for mgr in self._AllManagers():
      for event_type, methods in mgr.GetEventHandlers().iteritems():
        for method in methods:
          self._event_hub.Subscribe(event_type, method)

  def AddThread(self, thr):
    self._threads.add(thr)

  def GetWatchdogThread(self):
    return self._watchdog_thread

  def GetBackend(self):
    return self._backend

  def GetEventHub(self):
    return self._event_hub

  def GetTapManager(self):
    return self._tap_manager

  def GetFlowManager(self):
    return self._flow_manager

  def GetAuthenticationManager(self):
    return self._authentication_manager

  def GetThreads(self):
    return self._threads

  def SyncNow(self):
    """Visible for testing."""
    return self._sync_thread.sync_now()


class KegbotCoreApp(app.App):
  def __init__(self, name='core'):
    app.App.__init__(self, name)
    self._logger.info('Kegbot is starting up.')
    self._env = KegbotEnv()

  def _MainLoop(self):
    watchdog = self._env.GetWatchdogThread()
    while not self._do_quit:
      try:
        watchdog.join(0.5)
        if not watchdog.isAlive() and not self._do_quit:
          self._logger.error("Watchdog thread exited, quitting")
          self.Quit()
          return
      except KeyboardInterrupt:
        self._logger.info("Got keyboard interrupt, quitting")
        self.Quit()
        return

  def _Setup(self):
    app.App._Setup(self)
    for thr in self._env.GetThreads():
      self._AddAppThread(thr)
    self._env.GetEventHub().PublishEvent(kbevent.StartedEvent())

  def Quit(self):
    self._do_quit = True
    event = kbevent.QuitEvent()
    self._env.GetEventHub().PublishEvent(event)
    time.sleep(0.5)
    self._logger.info('Kegbot stopped.')

