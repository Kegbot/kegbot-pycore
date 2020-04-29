#!/usr/bin/env python
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

"""Unittest for flow_meter module"""

import unittest

from . import flow_meter

MAX_DELTA = 5000

class FlowMeterTestCase(unittest.TestCase):
  def setUp(self):
    self.meter = flow_meter.FlowMeter('test_meter', max_delta=MAX_DELTA)

  def _testSequence(self, meter, sequence, expected_total):
    for reading in sequence:
      meter.SetTicks(reading)
    total = meter.GetTicks()
    self.assertEqual(total, expected_total)

  def testBasicMeterUse(self):
    """Create a new flow device, perform basic operations on it."""
    # Our new device should have accumulated 0 ticks thus far.
    reading = self.meter.GetTicks()
    self.assertEqual(reading, 0)

    # Report an instantaneous reading of 2000 ticks. Since this is the first
    # reading, this should cause no change in the device ticks.
    self.meter.SetTicks(2000)
    reading = self.meter.GetTicks()
    self.assertEqual(reading, 0)

    # Report another instantaneous reading, which should now increment the flow
    self.meter.SetTicks(2100)
    reading = self.meter.GetTicks()
    self.assertEqual(reading, 100)

    # The FlowManager saves the last reading value; check it.
    last_reading = self.meter.GetLastReading()
    self.assertEqual(last_reading, 2100)

    # Report a reading that is much larger than the last reading. Values larger
    # than the constant common_defs.MAX_METER_READING_DELTA should be ignored by
    # the FlowManager.
    illegal_delta = MAX_DELTA + 1
    new_reading = last_reading + illegal_delta
    self.meter.SetTicks(new_reading)
    # The illegal update should not affect the ticks.
    vol = self.meter.GetTicks()
    self.assertEqual(vol, 100)
    # The value of the last update should be recorded, however.
    last_reading = self.meter.GetLastReading()
    self.assertEqual(last_reading, new_reading)

  def testBasicMeterUse2(self):
    self._testSequence(self.meter, (1000, 1100, 2100, 3100), 2100)

  def testOverflowHandling(self):
    first_reading = 2**32 - 100    # start with very large number
    second_reading = 2**32 - 50    # increment by 50
    overflow_reading = 10          # increment by 50+10 (overflow)

    self.meter.SetTicks(first_reading)
    curr_reading = self.meter.GetTicks()
    self.assertEqual(curr_reading, 0)

    self.meter.SetTicks(second_reading)
    curr_reading = self.meter.GetTicks()
    self.assertEqual(curr_reading, 50)

    self.meter.SetTicks(overflow_reading)
    curr_reading = self.meter.GetTicks()
    self.assertEqual(curr_reading, 50)

  def testNoOverflow(self):
    self.meter.SetTicks(0)
    curr_reading = self.meter.GetTicks()
    self.assertEqual(curr_reading, 0)

    self.meter.SetTicks(100)
    curr_reading = self.meter.GetTicks()
    self.assertEqual(curr_reading, 100)

    self.meter.SetTicks(10)
    curr_reading = self.meter.GetTicks()
    self.assertEqual(curr_reading, 100)

    self.meter.SetTicks(20)
    curr_reading = self.meter.GetTicks()
    self.assertEqual(curr_reading, 110)


if __name__ == '__main__':
  unittest.main()
