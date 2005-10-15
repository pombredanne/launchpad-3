#!/usr/bin/env python
# Copyright (c) 2005 Canonical Ltd.
# Author: David Allouche <david@allouche.net>

import logging

import pybaz as arch
from canonical.arch import broker
from importd import taxi

from importd.tests import test_Job, helpers, TestUtil


class TestImportVersion(helpers.TaxiTestCase):

    def setUp(self):
        helpers.TaxiTestCase.setUp(self)
        self.archive_manager.createMaster()
        self.archive_manager.createMirror()
        self.baz_tree_helper.setUpSigning()
        self.baz_tree_helper.setUpTree()
        self.baz_tree_helper.setUpBaseZero()
        self.version = self.archive_manager_helper.makeVersion()
        self.job = self.job_helper.makeJob()

    def setUpPatch(self):
        self.baz_tree_helper.setUpPatch()

    def transactionManager(self):
        return self.zopeless_helper.txn

    def mirror_location(self):
        return self.archive_manager._mirror

    def importBranch(self):
        aTaxi = taxi.Taxi(self.job)
        aTaxi.logger = TestUtil.makeSilentLogger()
        aTaxi.txnManager = self.transactionManager()
        aTaxi.importBranch()

    def assertDatabaseLevels(self, exist, not_exist):
        version = self.version
        db_archive = broker.Archives()[version.archive.name]
        self.failUnless(db_archive.exists())
        parser = arch.NameParser(version.fullname)
        db_category = db_archive[parser.get_category()]
        self.failUnless(db_category.exists())
        db_branch = db_category[parser.get_branch()]
        self.failUnless(db_branch.exists())
        db_version = db_branch[parser.get_version()]
        self.failUnless(db_version.exists())
        for level in exist:
            self.failUnless(db_version[level].exists(),
                            '%s does not exist in the database' % level)
        for level in not_exist:
            self.failIf(db_version[level].exists(),
                        '%s exists in the database' % level)

    def assertArchiveNotInDatabase(self):
        db_archive = broker.Archives()[self.version.archive.name]
        self.failIf(db_archive.exists())

    def test_initial_sync(self):
        """Taxi.importBranch works for an initial sync."""
        self.assertArchiveNotInDatabase()
        self.setUpPatch()
        self.importBranch()
        self.assertDatabaseLevels(['base-0', 'patch-1'], ['patch-2'])
        self.assertMirrorPatchlevels(['base-0', 'patch-1'])

    def test_idempotent_sync(self):
        """Taxi.importBranch works for a second sync WITHOUT no new data."""
        self.test_initial_sync()
        self.importBranch()
        self.assertDatabaseLevels(['base-0', 'patch-1'], ['patch-2'])
        self.assertMirrorPatchlevels(['base-0', 'patch-1'])

    def test_second_sync(self):
        """Taxi.importBranch works for a second sync WITH new data."""
        self.assertArchiveNotInDatabase()
        self.importBranch()
        self.assertDatabaseLevels(['base-0'], ['patch-1'])
        self.assertMirrorPatchlevels(['base-0'])
        self.setUpPatch()
        self.importBranch()
        self.assertDatabaseLevels(['base-0', 'patch-1'], ['patch-2'])
        self.assertMirrorPatchlevels(['base-0', 'patch-1'])

    def test_refresh_sync(self):
        """Taxi.importBranch refreshes a mirrored revision correctly."""
        self.mirrorBranch() # make database out of date
        self.assertArchiveNotInDatabase()
        self.assertMirrorPatchlevels(['base-0'])
        self.setUpPatch()
        self.importBranch()
        self.assertDatabaseLevels(['base-0', 'patch-1'], ['patch-2'])
        self.assertMirrorPatchlevels(['base-0', 'patch-1'])


TestUtil.register(__name__)

