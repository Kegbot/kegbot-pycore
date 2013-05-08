#!/usr/bin/env python

"""Unittest for kegnet module"""

import asyncore
import logging
import unittest

import gflags

from . import kegnet

FLAGS = gflags.FLAGS

LOGGER = logging.getLogger('myunittest')

TEST_ADDR = ':0'  # localhost, random port

class KegnetTestCase(unittest.TestCase):
  def setUp(self):
    self.server = kegnet.KegnetServer(name='kegnet', kb_env=None,
        addr=TEST_ADDR)
    self.server.StartServer()
    self.port = self.server.getsockname()[1]
    print 'Server started on port %s' % self.port

  def testSimpleFlow(self):
    print 'Looping'
    asyncore.loop(timeout=1, count=1)
    addr = ':%s' % (self.port,)
    print 'New client, connecting to addr=%s' % addr
    client = kegnet.KegnetClient(addr=addr)
    client.SendFlowStart('mytap')
    asyncore.loop(timeout=1, count=1)
    print 'Done'

if __name__ == '__main__':
  import sys
  logging.basicConfig(stream=sys.stderr)
  LOGGER.setLevel(logging.DEBUG)
  LOGGER.info('here i am!')
  unittest.main()
