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
