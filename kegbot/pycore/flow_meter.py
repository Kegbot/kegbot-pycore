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

"""Utility module for summing flows."""

import logging

class FlowMeter(object):
  """Represents a tick-accumulating flow sensor."""
  def __init__(self, name, max_delta=0):
    self._name = name
    self._max_delta = max_delta
    self._last_ticks = None
    self._total_ticks = 0
    self._logger = logging.getLogger('flowmeter-%s' % self._name)

  def __str__(self):
    return "<FlowMeter name=%s ticks=%i>" % (self._name, self.GetTicks())

  def SetTicks(self, ticks):
    """Reports the instantaneous reading of the meter.

    If this is the first report, `_total_ticks` is set to 0.

    For all subsequent reports, a delta is computed by subtracting `_last_ticks`
    from `ticks`.  If the delta is positive and does not exceed `_max_delta`, it
    is added to `_total_ticks`.  If the delta is negative or exceeds
    `_max_delta`, the delta is ignored.

    The value `ticks` is always saved as `_last_ticks` for use in the next
    report.
    """
    ticks = long(ticks)
    self._logger.info('SetTicks: ticks=%s last=%s total=%s' % (
        ticks, self._last_ticks, self._total_ticks))

    delta = 0
    if self._last_ticks is not None:
      delta = ticks - self._last_ticks
      if delta > 0 and (not self._max_delta or delta <= self._max_delta):
        self._total_ticks += delta
      else:
        self._logger.warning('Bad ticks report: ticks=%i last=%i' %
            (ticks, self._last_ticks))
        delta = 0

    self._last_ticks = ticks
    return delta

  def GetTicks(self):
    return self._total_ticks

  def GetLastReading(self):
    return self._last_ticks

  def GetName(self):
    return self._name

