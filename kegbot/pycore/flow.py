# Copyright 2012 Mike Wakerly <opensource@hoho.com>
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

"""Module for the Flow data structure."""

import datetime
from . import kbevent

class Flow:
  """An object that holds data about a pour while it is active."""
  def __init__(self, meter_name, flow_id, username=None, max_idle_secs=10, when=None):
    self._meter_name = meter_name
    self._flow_id = flow_id
    self._bound_username = username
    self._max_idle = datetime.timedelta(seconds=max_idle_secs)
    self._state = kbevent.FlowUpdate.FlowState.ACTIVE
    if when is None:
      when = datetime.datetime.now()
    self._start_time = when
    self._end_time = when
    self._last_log_time = None
    self._total_ticks = 0L
    self._volume_ml = None 

  def __str__(self):
    return '<Flow 0x%08x: meter_name=%s ticks=%s username=%s max_idle=%s>' % (self._flow_id,
        self._meter_name, self._total_ticks, repr(self._bound_username),
        self._max_idle)

  def GetUpdateEvent(self):
    event = kbevent.FlowUpdate()
    event.flow_id = self._flow_id
    event.meter_name = self._meter_name
    event.state = self._state

    if self._bound_username:
      event.username = self._bound_username

    event.start_time = self._start_time
    event.last_activity_time = self._end_time
    event.ticks = self.GetTicks()
    event.volume_ml = self.GetVolumeMl()

    return event

  def AddTicks(self, amount, when=None, tap=None):
    self._total_ticks += amount
    if when is None:
      when = datetime.datetime.now()
    self._end_time = when
    if tap is not None:
        self._volume_ml = tap.TicksToMilliliters(self._total_ticks)

  def GetId(self):
    return self._flow_id

  def GetState(self):
    return self._state

  def SetState(self, state):
    self._state = state

  def GetTicks(self):
    return self._total_ticks

  def GetVolumeMl(self):
    return self._volume_ml

  def GetUsername(self):
    return self._bound_username

  def SetUsername(self, username):
    self._bound_username = username

  def GetMeterName(self):
    return self._meter_name

  def IsIdle(self, when=None):
    if when is None:
      when = datetime.datetime.now()
    idle_time = when - self._end_time
    return idle_time > self._max_idle

