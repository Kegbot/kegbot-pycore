"""Module for the Tap data structure."""

from builtins import object
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

