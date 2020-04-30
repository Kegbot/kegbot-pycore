"""Unittest for tap module"""

import unittest
from . import tap

class TapTestCase(unittest.TestCase):
  def setUp(self):
    self.tap = tap.Tap('tap', 100, 'relay')

  def testEquals(self):
    other = tap.Tap('tap', 100, 'relay')
    self.assertEqual(self.tap, other)

    other = tap.Tap('xtap', 100, 'relay')
    self.assertNotEqual(self.tap, other)

  def testMethods(self):
    expected = ('tap', 100, 'relay')
    self.assertEqual(expected, self.tap.AsTuple())

    self.assertEqual('tap', self.tap.GetName())
    self.assertEqual('relay', self.tap.GetRelayName())
    self.assertEqual(100.0, self.tap.TicksToMilliliters(1))

