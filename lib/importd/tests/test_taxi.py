#!/usr/bin/env python
# Copyright (c) 2005 Canonical Ltd.
# Author: David Allouche <david@allouche.net>

import logging

import pybaz as arch
from canonical.arch import broker
from importd import taxi

from canonical.launchpad.ftests import harness
import test_Job
import TestUtil

from canonical.ftests import pgsql


class ZopelessTestSetup(harness.LaunchpadZopelessTestSetup):
    dbuser = 'importd'

    # XXX Someone please find a way to use zopeless tests without the test.py
    # launchpad runner, and without having to do evil magic like explicitly
    # setting up and tearing down the fake connection.
    # -- David Allouche 2005-05-11

    def setUp(self):
        pgsql.installFakeConnect()
        harness.LaunchpadZopelessTestSetup.setUp(self)

    def tearDown(self):
        harness.LaunchpadZopelessTestSetup.tearDown(self)
        pgsql.uninstallFakeConnect()


class TestImportVersion(test_Job.ArchiveTestCase):

    version_fullname = "jo@example.com/foo-bar--HEAD--0"

    def setUp(self):
        test_Job.ArchiveTestCase.setUp(self)
        self._zopeless = ZopelessTestSetup()
        self._zopeless.setUp()
        self.setupArchArchive(self.version_fullname)
        self.setupArchMirror(self.version_fullname)
        self.setupArchTree(self.version_fullname)
        self.setupBaseZero()

    def tearDown(self):
        self._zopeless.tearDown()
        test_Job.ArchiveTestCase.tearDown(self)

    def importVersion(self):
        aTaxi = taxi.Taxi()
        aTaxi.logger = logging
        aTaxi.txnManager = self._zopeless.txn
        mirror = arch.Archive(self.baz_archive.name + '-MIRROR')
        aTaxi.importVersion(arch.Version(self.version_fullname),
                            mirror.location,
                            test_Job.sampleData.product_id,
                            'title of the branch',
                            'description of the branch')

    def assertDatabaseLevels(self, exist, not_exist):
        version = arch.Version(self.version_fullname)
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

    def assertMirrorLevels(self, expected):
        version = arch.Version(self.version_fullname)
        mirror_name = self.baz_archive.name + '-MIRROR'
        mirror_version = arch.Version(mirror_name + '/' + version.nonarch)
        levels = [revision.patchlevel
                  for revision in mirror_version.iter_revisions()]
        self.assertEqual(levels, expected)

    def test_initial_sync(self):
        """Taxi.importVersion works for an initial sync."""
        self.assertArchiveNotInDatabase()
        self.setupPatchOne()
        self.importVersion()
        self.assertDatabaseLevels(['base-0', 'patch-1'], ['patch-2'])
        self.assertMirrorLevels(['base-0', 'patch-1'])

    def test_idempotent_sync(self):
        """Taxi.importVersion works for a second sync WITHOUT no new data."""
        self.test_initial_sync()
        self.importVersion()
        self.assertDatabaseLevels(['base-0', 'patch-1'], ['patch-2'])
        self.assertMirrorLevels(['base-0', 'patch-1'])

    def test_second_sync(self):
        """Taxi.importVersion works for a second sync WITH new data."""
        self.assertArchiveNotInDatabase()
        self.importVersion()
        self.assertDatabaseLevels(['base-0'], ['patch-1'])
        self.assertMirrorLevels(['base-0'])
        self.setupPatchOne()
        self.importVersion()
        self.assertDatabaseLevels(['base-0', 'patch-1'], ['patch-2'])
        self.assertMirrorLevels(['base-0', 'patch-1'])

    def assertArchiveNotInDatabase(self):
        version = arch.Version(self.version_fullname)
        db_archive = broker.Archives()[version.archive.name]
        self.failIf(db_archive.exists())

    def test_refresh_sync(self):
        """Taxi.importVersion refreshes a mirrored revision correctly."""
        self.baz_archive.mirror() # make database out of date
        self.assertArchiveNotInDatabase()
        self.assertMirrorLevels(['base-0'])
        self.setupPatchOne()
        self.importVersion()
        self.assertDatabaseLevels(['base-0', 'patch-1'], ['patch-2'])
        self.assertMirrorLevels(['base-0', 'patch-1'])


TestUtil.register(__name__)

