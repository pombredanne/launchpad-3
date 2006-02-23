# Copyright 2006 Canonical Ltd.  All rights reserved.
"""Fail if the chunkydiff option is off.

This ensures that people can't accidently commit the main config file with
this option turned off to rocketfuel.
"""
__metaclass__ = type

import unittest
from canonical.config import config

class TestChunkydiffIsOn(unittest.TestCase):

    def test(self):
        self.failUnless(
                config.chunkydiff is True,
                'This test is failing to ensure that the chunkydiff '
                'config setting cannot be committed in "off" mode.'
                )

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
