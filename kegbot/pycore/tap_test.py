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

