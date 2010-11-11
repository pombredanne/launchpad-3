# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Fail if the chunkydiff option is off.

This ensures that people can't accidently commit the main config file with
this option turned off to rocketfuel.
"""
__metaclass__ = type

import unittest

from canonical.config import config


class TestChunkydiffSetting(unittest.TestCase):

    def test(self):
        self.failUnless(
                config.canonical.chunkydiff is False,
                'This test is failing to ensure that the chunkydiff '
                'config setting cannot be committed in "on" mode.'
                )

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
