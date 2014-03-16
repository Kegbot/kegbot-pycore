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

"""Unittest for flow module"""

import datetime
import unittest
from . import flow

class FlowTestCase(unittest.TestCase):
  def setUp(self):
    self.meter_name = 'test.meter'
    self.flow = flow.Flow(self.meter_name, 123, username=None, max_idle_secs=10,
        when=datetime.datetime.fromtimestamp(0))

  def testAddTicks(self):
    self.assertEquals(0, self.flow.GetTicks())
    self.flow.AddTicks(100)
    self.assertEquals(100, self.flow.GetTicks())

  def testGetUpdateEvent(self):
    self.flow.AddTicks(10, when=datetime.datetime.fromtimestamp(20))
    e = self.flow.GetUpdateEvent()

    self.assertEquals(None, e.username)
    self.assertEquals(123, e.flow_id)
    self.assertEquals(self.meter_name, e.meter_name)
    self.assertEquals('active', e.state)
    self.assertEquals(datetime.datetime.fromtimestamp(0), e.start_time)
    self.assertEquals(datetime.datetime.fromtimestamp(20), e.last_activity_time)
    self.assertEquals(10, e.ticks)
