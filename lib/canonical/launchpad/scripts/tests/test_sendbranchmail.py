#! /usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Test the sendbranchmail script"""

import unittest
from canonical.testing import DatabaseLayer
from canonical.launchpad.scripts.tests import run_script

class TestSendcodemail(unittest.TestCase):

    layer = DatabaseLayer

    def test_sendcodemail(self):
        retcode, stdout, stderr = run_script(
            'cronscripts/sendbranchmail.py', [])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
