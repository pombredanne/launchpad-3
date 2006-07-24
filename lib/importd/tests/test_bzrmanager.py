# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Tests for the bzr back-end to importd."""

__metaclass__ = type

__all__ = ['test_suite']

import unittest

from importd.bzrmanager import BzrManager
from importd.tests import helpers, testutil


class TestNoopMethods(unittest.TestCase):
    """Check presence of no-op methods needed for ArchiveManager compatibility.

    The methods tested in this class are not expected to do anything, but they
    must be present for compatibility with the ArchiveManager API.
    """

    def setUp(self):
        self.bzr_manager = BzrManager()

    def testCreateMaster(self):
        # BzrManager.createMaster can be called.
        self.bzr_manager.createMaster()

    def testCreateMirror(self):
        # BzrManager.createMirror can be called.
        self.bzr_manager.createMirror()

    def testNukeMaster(self):
        # BzrManager.nukeMaster can be called
        self.bzr_manager.nukeMaster()

    def testRollbackToMirror(self):
        # BzrManager.rollbackToMirror can be called
        self.bzr_manager.rollbackToMirror()


testutil.register(__name__)

