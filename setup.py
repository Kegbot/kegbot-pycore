"""Standalone Python Kegbot Core.

For more information, see http://kegbot.org/docs/pycore/
"""
from setuptools import setup, find_packages

DOCLINES = __doc__.split('\n')

VERSION = '1.3.0b1'
SHORT_DESCRIPTION = DOCLINES[0]
LONG_DESCRIPTION = '\n'.join(DOCLINES[2:])

setup(
  name = 'kegbot-pycore',
  version = VERSION,
  description = SHORT_DESCRIPTION,
  long_description = LONG_DESCRIPTION,
  author='The Kegbot Project Contributors',
  author_email='info@kegbot.org',
  url='https://kegbot.org/',
  packages = find_packages(exclude=['testdata']),
  namespace_packages = ['kegbot'],
  scripts = [
    'bin/kegboard_daemon.py',
    'bin/kegbot_core.py',
    'bin/lcd_daemon.py',
    'bin/rfid_daemon.py',
    'bin/test_flow.py',
  ],
  include_package_data = True,
)

