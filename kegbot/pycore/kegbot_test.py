#!/usr/bin/env python

"""Unittest for kegbot module"""

import logging
import unittest

from kegbot.util import util

from . import backend
from . import kbevent
from . import kegbot_app

LOGGER = logging.getLogger('unittest')

TEST_TAPS = [
  {
    'meter_name': 'testflow0',
    'description': 'Test Tap #0',
    'ml_per_tick': 0.5,
    'relay_name': 'testrelay0',
    'id': 1,
    'name': 'Test Tap #0',
  },
  {
    'meter_name': 'testflow1',
    'description': 'Test Tap #1',
    'ml_per_tick': 2.0,
    'relay_name': 'testrelay1',
    'id': 2,
    'name': 'Test Tap #1',
  }
]

class TestBackend(backend.Backend):
  def GetStatus(self):
    return {
      'taps': self.GetAllTaps(),
    }

  def GetAllTaps(self):
    return [util.AttrDict(d) for d in TEST_TAPS]

class KegbotTestCase(unittest.TestCase):
  def setUp(self):
    self.kb = kegbot_app.KegbotEnv(backend_obj=TestBackend())
    self.hub = self.kb.GetEventHub()
    self.hub._debug = True

    self.hub.PublishEvent(kbevent.StartedEvent())
    self.Flush()

  def Flush(self):
    self.hub.Flush()

  def testTapSyncNormal(self):
    self.kb.SyncNow()
    self.Flush()

    tap_manager = self.kb.GetTapManager()

    taps = tap_manager.GetAllTaps()
    self.assertEquals(2, len(taps))

  def testPour(self):
    e = kbevent.MeterUpdate()
    e.meter_name = 'testflow0'
    e.reading = 100
    self.hub.PublishEvent(e)

    e = kbevent.MeterUpdate()
    e.meter_name = 'testflow0'
    e.reading = 200
    self.hub.PublishEvent(e)

    self.Flush()

    flow_manager = self.kb.GetFlowManager()
    flows = flow_manager.GetActiveFlows()
    self.assertEqual(1, len(flows))

if __name__ == '__main__':
  unittest.main()
