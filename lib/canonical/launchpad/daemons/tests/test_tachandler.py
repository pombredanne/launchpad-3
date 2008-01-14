# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Tests for canonical.launchpad.daemons.tachandler"""

__metaclass__ = type

import unittest
import tempfile
import os.path

from canonical.launchpad.daemons.tachandler import TacTestSetup, TacException


class TacTestSetupTestCase(unittest.TestCase):
    """Some tests for the error handling of TacTestSetup."""

    def test_missingTac(self):
        """TacTestSetup raises TacException if the tacfile doesn't exist"""
        class MissingTac(TacTestSetup):
            root = '/'
            tacfile = '/file/does/not/exist'
            pidfile = tacfile
            logfile = tacfile
            def setUpRoot(self):
                pass

        self.assertRaises(TacException, MissingTac().setUp)

    def test_couldNotListenTac(self):
        """If the tac fails due to not being able to listen on the needed port,
        TacTestSetup will fail.
        """
        class CouldNotListenTac(TacTestSetup):
            root = os.path.dirname(__file__)
            tacfile = os.path.join(root, 'cannotlisten.tac')
            pidfile = os.path.join(tempfile.gettempdir(), 'cannotlisten.pid')
            logfile = os.path.join(tempfile.gettempdir(), 'cannotlisten.log')
            def setUpRoot(self):
                pass

        self.assertRaises(TacException, CouldNotListenTac().setUp)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TacTestSetupTestCase))
    return suite

