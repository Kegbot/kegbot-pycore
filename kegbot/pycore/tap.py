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

"""Module for the Tap data structure."""

class Tap(object):
  """An object that holds data about a configured beverage tap."""
  def __init__(self, name, ml_per_tick, relay_name=None):
    self._name = name
    self._ml_per_tick = float(ml_per_tick)
    self._relay_name = relay_name

  def __str__(self):
    return "<Tap name=%s ml_per_tick=%s relay_name=%s>" % (
        self._name, self._ml_per_tick, self._relay_name)

  def __eq__(self, other):
    return not not other and self.AsTuple() == other.AsTuple()

  def AsTuple(self):
    return self._name, self._ml_per_tick, self._relay_name

  def GetName(self):
    return self._name

  def GetRelayName(self):
    return self._relay_name

  def TicksToMilliliters(self, ticks):
    return self._ml_per_tick * ticks

