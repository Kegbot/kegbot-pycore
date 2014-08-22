#!/usr/bin/env python
"""Standalone Python Kegbot Core.

For more information, see http://kegbot.org/docs/pycore/
"""
from setuptools import setup, find_packages

DOCLINES = __doc__.split('\n')

VERSION = '1.2.0'
SHORT_DESCRIPTION = DOCLINES[0]
LONG_DESCRIPTION = '\n'.join(DOCLINES[2:])

def setup_package():
  setup(
      name = 'kegbot-pycore',
      version = VERSION,
      description = SHORT_DESCRIPTION,
      long_description = LONG_DESCRIPTION,
      author = 'Bevbot LLC',
      author_email = 'info@bevbot.com',
      url = 'https://kegbot.org/docs/pycore',
      packages = find_packages(exclude=['testdata']),
      namespace_packages = ['kegbot'],
      scripts = [
        'bin/kegboard_daemon.py',
        'bin/kegbot_core.py',
        'bin/lcd_daemon.py',
        'bin/rfid_daemon.py',
        'bin/test_flow.py',
      ],
      install_requires = [
        'kegbot-pyutils == 0.1.7',
        'kegbot-api >= 0.1.17',
        'kegbot-kegboard == 1.1.2',
        'redis >= 2.9.1, < 3.0',

        'python-gflags == 2.0',
      ],
      include_package_data = True,
  )

if __name__ == '__main__':
  setup_package()
