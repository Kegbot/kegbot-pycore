#!/usr/bin/env python

"""Unittest for manager module"""

import datetime
import unittest

from . import common_defs
from . import kbevent
from . import manager

class FlowManagerTestCase(unittest.TestCase):
  def setUp(self):
    event_hub = kbevent.EventHub()
    backend = None
    self.tap_manager = manager.TapManager(event_hub, backend)
    self.flow_manager = manager.FlowManager(event_hub, self.tap_manager)
    self.tap_manager._RegisterOrUpdateTap(name='flow0', ml_per_tick=1000/2200.0)

  def tearDown(self):
    del self.tap_manager._taps['flow0']

  def testBasicMeterUse(self):
    """Create a new flow device, perform basic operations on it."""
    # Duplicate registration should cause an exception.
    #self.assertRaises(manager.AlreadyRegisteredError,
    #                  self.tap_manager.RegisterTap, 'flow0', 0, 0)

    self.assertIsNone(self.tap_manager.GetTap('flow_unknown'))

    # Our new device should have accumulated 0 volume thus far.
    tap = self.tap_manager.GetTap('flow0')
    meter = self.flow_manager.GetMeter('flow0')
    self.assertEqual(meter.GetTicks(), 0L)

    # Report an instantaneous reading of 2000 ticks. Since this is the first
    # reading, this should cause no change in the device volume.
    flow, is_new = self.flow_manager.UpdateFlow(tap.GetName(), 2000)
    self.assertEqual(meter.GetTicks(), 0L)
    self.assertIsNotNone(flow)
    self.assertTrue(is_new)

    # Report another instantaneous reading, which should now increment the flow
    new_flow, is_new = self.flow_manager.UpdateFlow(tap.GetName(), 2100)
    self.assertEqual(meter.GetTicks(), 100L)
    self.assertFalse(is_new)
    self.assertIs(flow, new_flow)

    # The FlowManager saves the last reading value; check it.
    self.assertEqual(meter.GetLastReading(), 2100)

    # Report a reading that is much larger than the last reading. Values larger
    # than the constant common_defs.MAX_METER_READING_DELTA should be ignored by
    # the FlowManager.
    meter_reading = meter.GetLastReading()
    illegal_delta = common_defs.MAX_METER_READING_DELTA + 100
    new_reading = meter_reading + illegal_delta

    # The illegal update should not affect the volume.
    new_flow, is_new = self.flow_manager.UpdateFlow(tap.GetName(), new_reading)
    self.assertFalse(is_new)
    self.assertIs(flow, new_flow)
    self.assertEqual(meter.GetTicks(), 100)

    # The value of the last update should be recorded, however.
    self.assertEqual(meter.GetLastReading(), new_reading)

  def testOverflowHandling(self):
    first_reading = 2**32 - 100    # start with very large number
    second_reading = 2**32 - 50    # increment by 50
    overflow_reading = 10          # increment by 50+10 (overflow)

    flow, is_new = self.flow_manager.UpdateFlow('flow0', first_reading)
    self.assertIsNotNone(flow)
    self.assertTrue(is_new)
    self.assertEqual(0, flow.GetTicks())

    new_flow, is_new = self.flow_manager.UpdateFlow('flow0', second_reading)
    self.assertIs(flow, new_flow)
    self.assertFalse(is_new)
    self.assertEqual(50, flow.GetTicks())

    new_flow, is_new = self.flow_manager.UpdateFlow('flow0', overflow_reading)
    self.assertIs(flow, new_flow)
    self.assertFalse(is_new)
    self.assertEqual(50, flow.GetTicks())

  def testNoOverflow(self):
    flow, is_new = self.flow_manager.UpdateFlow('flow0', 0)
    self.assertIsNotNone(flow)
    self.assertTrue(is_new)
    self.assertEqual(0, flow.GetTicks())

    new_flow, is_new = self.flow_manager.UpdateFlow('flow0', 100)
    self.assertIs(flow, new_flow)
    self.assertFalse(is_new)
    self.assertEqual(100, flow.GetTicks())

    new_flow, is_new = self.flow_manager.UpdateFlow('flow0', 10)
    self.assertIs(flow, new_flow)
    self.assertFalse(is_new)
    self.assertEqual(100, flow.GetTicks())

    new_flow, is_new = self.flow_manager.UpdateFlow('flow0', 20)
    self.assertIs(flow, new_flow)
    self.assertFalse(is_new)
    self.assertEqual(110, flow.GetTicks())

  def testActivityMonitoring(self):
    def t(stamp):
      return datetime.datetime.fromtimestamp(stamp)

    flow, is_new = self.flow_manager.UpdateFlow('flow0', 0, when=t(0))
    self.assertIsNotNone(flow)
    self.assertTrue(is_new)

    self.assertFalse(flow.IsIdle(when=t(0)))
    self.assertTrue(flow.IsIdle(when=t(1000)))

    idle_flows = list(self.flow_manager.IterIdleFlows(when=t(0)))
    self.assertTrue(len(idle_flows) == 0)

    idle_flows = list(self.flow_manager.IterIdleFlows(when=t(1000)))
    self.assertTrue(len(idle_flows) == 1)


if __name__ == '__main__':
  unittest.main()
