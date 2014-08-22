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

"""Kegbot API implementation of Backend."""

import logging
import socket

from kegbot.api import kbapi
from . import common_defs

class BackendException(Exception):
  """Base exception type."""


class DoesNotExistException(BackendException):
  """Thrown when operating against a non-existing resource."""


class Backend(object):

  def GetStatus(self):
    raise NotImplementedError

  def GetAllTaps(self):
    raise NotImplementedError

  def RecordDrink(self, tap_name, ticks, volume_ml=None, username=None,
      pour_time=None, duration=0, auth_token=None, spilled=False, shout=''):
    raise NotImplementedError

  def CancelDrink(self, drink_id, spilled=False):
    raise NotImplementedError

  def LogSensorReading(self, sensor_name, temperature, when=None):
    raise NotImplementedError

  def GetAuthToken(self, auth_device, token_value):
    raise NotImplementedError

  def CreateController(self, controller_name):
    raise NotImplementedError

class WebBackend(Backend):
  def __init__(self, api_url=None, api_key=None):
    self._logger = logging.getLogger('api-backend')
    self._client = kbapi.Client(api_url=api_url, api_key=api_key)

  def GetStatus(self):
    return self._client.status()

  def GetAllTaps(self):
    return self._client.taps()

  def RecordDrink(self, meter_name, ticks, volume_ml=None, username=None,
      pour_time=None, duration=0, auth_token=None, spilled=False, shout=''):
    try:
      return self._client.record_drink(tap_name=meter_name, ticks=ticks,
          volume_ml=volume_ml, username=username, pour_time=pour_time,
          duration=duration, auth_token=auth_token, spilled=spilled,
          shout=shout)
    except kbapi.NotFoundError as e:
      raise DoesNotExistException('Cannot record against meter "%s": %s' % (meter_name, e))
    except kbapi.Error as e:
      raise BackendException(e)

  def CancelDrink(self, seqn, spilled=False):
    try:
      return self._client.cancel_drink(seqn, spilled)
    except kbapi.Error as e:
      raise BackendException(e)

  def LogSensorReading(self, sensor_name, temperature, when=None):
    # If the temperature is out of bounds, reject it.
    min_val = common_defs.THERMO_SENSOR_RANGE[0]
    max_val = common_defs.THERMO_SENSOR_RANGE[1]
    if temperature < min_val or temperature > max_val:
      raise ValueError, 'Temperature out of bounds'

    try:
      return self._client.log_sensor_reading(sensor_name, temperature, when)
    except kbapi.NotFoundError:
      self._logger.warning('No sensor on backend named "%s"' % (sensor_name,))
      return None
    except kbapi.ServerError:
      self._logger.warning('Server error recording temperature; dropping reading.')
      return None
    except socket.error:
      self._logger.warning('Socket error recording temperature; dropping reading.')
      return None

  def GetAuthToken(self, auth_device, token_value):
    try:
      return self._client.get_token(auth_device, token_value)
    except kbapi.NotFoundError:
      raise
    except socket.error:
      self._logger.warning('Socket error fetching token; ignoring.')
      raise kbapi.NotFoundError()

  def CreateController(self, controller_name):
    try:
      controller = self._client.create_controller(controller_name)
      # Create default meters.
      for meter in ('flow0', 'flow1'):
        self._client.create_flow_meter(controller['id'], meter)
      return controller
    except kbapi.Error as e:
      raise BackendException(e)
