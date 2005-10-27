#!/usr/bin/env python
# Copyright (c) 2005 Canonical Ltd.
# Author: David Allouche <david@allouche.net>

import os
import shutil
import unittest

import gnarly.process
import gnarly.process.unix_process
gnarly.process.Popen = gnarly.process.unix_process.Popen

import pybaz.errors
import pybaz as arch
import pybaz.backends.forkexec
pybaz.backend.spawning_strategy = pybaz.backends.forkexec.PyArchSpawningStrategy

from importd import archivemanager
from importd.tests import helpers, TestUtil


__all__ = ['test_suite']


class TestArchiveCreation(helpers.ArchiveManagerTestCase):

    def setUp(self):
        helpers.ArchiveManagerTestCase.setUp(self)
        self.sandbox_path = self.sandbox_helper.sandbox_path
        self.archive_name = self.job_helper.makeJob().archivename
        self.master = self.archive_manager._master
        self.mirror = self.archive_manager._mirror

    def testMasterUrl(self):
        """ArchiveManager._master.url is the expected value."""
        master_path = os.path.join(
            self.sandbox_path, 'archives', self.archive_name)
        self.assertEqual(self.master.url, master_path)

    def testMirrorUrl(self):
        """ArchiveManager._mirror.url is the expected value."""
        mirror_path = os.path.join(
            self.sandbox_path, 'mirrors', self.archive_name)
        self.assertEqual(self.mirror.url, mirror_path)

    def testCreateMaster(self):
        """ArchiveManager.createMaster() works"""
        master = self.master
        assert not master.is_registered()
        assert not os.path.exists(master.url)
        self.archive_manager.createMaster()
        self.failUnless(master.is_registered())
        self.failUnless(os.path.exists(master.url))
        self.failIf(master._meta_info_present('mirror'))
        self.failIf(master._meta_info_present('http-blows'))
        self.failUnless(master._meta_info_present('signed-archive'))
        self.assertEqual(master.meta_info('name'), self.archive_name)

    def testCreateMirror(self):
        """ArchiveManager.createMaster() works"""
        self.archive_manager.createMaster()
        mirror = self.mirror
        assert not mirror.is_registered()
        assert not os.path.exists(mirror.url)
        self.archive_manager.createMirror()
        self.failUnless(mirror.is_registered())
        self.failUnless(os.path.exists(mirror.url))
        self.failUnless(mirror._meta_info_present('mirror'))
        self.failUnless(mirror._meta_info_present('http-blows'))
        self.failUnless(mirror._meta_info_present('signed-archive'))
        self.assertEqual(mirror.meta_info('name'), self.archive_name)


class TestNukeMaster(helpers.BazTreeTestCase):

    def setUp(self):
        helpers.BazTreeTestCase.setUp(self)
        self.master = self.archive_manager._master
        self.version = self.archive_manager_helper.makeVersion()

    def masterVersions(self):
        master = self.archive_manager._master
        versions = self.version.archive.iter_location_versions(master)
        return list(versions)

    def testNukeMasterMissingArchive(self):
        """ArchiveManager.nukeMaster works with non-existent master archive."""
        assert not os.path.exists(self.master.url)
        self.archive_manager.nukeMaster()
        # nukeMaster has nothing to do, but must not fail

    def testNukeMasterMissingBranch(self):
        """ArchiveManager.nukeMaster works with non-existent master branch."""
        self.archive_manager.createMaster()
        assert os.path.exists(self.master.url)
        assert self.masterVersions() == []
        self.archive_manager.nukeMaster()
        # nukeMaster still has nothing to do, but must still not fail

    def testNukeMasterPopulated(self):
        """ArchiveManager.nukeMaster works with a populated master branch."""
        self.archive_manager.createMaster()
        # it must work with an existent but empty mirror
        self.archive_manager.createMirror()
        assert os.path.exists(self.master.url)
        self.baz_tree_helper.setUpSigning()
        self.baz_tree_helper.setUpTree()
        self.baz_tree_helper.setUpBaseZero()
        assert self.masterPatchlevels() == ['base-0']
        self.archive_manager.nukeMaster()
        self.failUnless(os.path.exists(self.master.url))
        self.assertEqual(self.masterVersions(), [])

    def testNukeMasterMirrored(self):
        self.archive_manager.createMaster()
        self.archive_manager.createMirror()
        assert os.path.exists(self.master.url)
        self.baz_tree_helper.setUpSigning()
        self.baz_tree_helper.setUpTree()
        self.baz_tree_helper.setUpBaseZero()
        self.mirrorBranch()
        assert self.masterPatchlevels() == ['base-0']
        assert self.mirrorPatchlevels() == ['base-0']
        self.assertRaises(archivemanager.NukeMirroredMasterError,
                          self.archive_manager.nukeMaster)
        self.assertEqual(self.masterPatchlevels(), ['base-0'])
        self.assertEqual(self.mirrorPatchlevels(), ['base-0'])


class TestRollbackToMirror(helpers.BazTreeTestCase):
    """Archive rollback, time-translate a version to the point of the mirror"""

    def setUp(self):
        helpers.BazTreeTestCase.setUp(self)
        self.version = self.archive_manager_helper.makeVersion()
        self.archive_manager.createMaster()
        self.archive_manager.createMirror()
        self.baz_tree_helper.setUpSigning()
        self.baz_tree_helper.setUpTree()

    def setUpRevlib(self):
        sandbox_path = self.sandbox_helper.sandbox_path
        revlib_path = os.path.join(sandbox_path, 'revlib')
        os.mkdir(revlib_path)
        arch.register_revision_library(revlib_path)

    def setUpBaseZero(self):
        self.baz_tree_helper.setUpBaseZero()

    def setUpPatch(self):
        self.baz_tree_helper.setUpPatch()

    def cleanUpTree(self):
        self.baz_tree_helper.cleanUpTree()

    def setUpEmptyMirrorVersion(self):
        mirror = self.archive_manager._mirror
        os.mkdir(os.path.join(mirror.url, self.version.nonarch))

    def masterVersions(self):
        master = self.archive_manager._master
        versions = self.version.archive.iter_location_versions(master)
        return list(versions)

    def removeMasterBranch(self):
        archive_path = self.archive_manager._master.url
        branch_path = os.path.join(archive_path, self.version.nonarch)
        shutil.rmtree(branch_path)

    def rollbackToMirror(self):
        self.archive_manager.rollbackToMirror()

    def rollbackToLevels(self, patchlevels):
        saved_method = self.archive_manager._locationPatchlevels
        def override_method(location):
            if location == self.archive_manager._mirror:
                return patchlevels
            else:
                return saved_method(location)
        self.archive_manager._locationPatchlevels = override_method
        try:
            self.rollbackToMirror()
        finally:
            self.archive_manager._locationPatchlevels = saved_method

    def testRollackFailIfRevlib(self):
        """rollbackToMirror fails with RuntimeError is a revlib is present"""
        self.setUpRevlib()
        self.assertRaises(archivemanager.RevisionLibraryPresentError,
                          self.rollbackToMirror)

    def testNoMirrorOrMaster(self):
        """rollbackToMirror is safe when branch does not exist at all"""
        self.rollbackToMirror()

    def testMirrorUpToDate(self):
        """rollbackToMirror is safe when mirror is up to date"""
        self.setUpBaseZero()
        self.setUpPatch()
        assert self.masterPatchlevels() == ['base-0', 'patch-1']
        self.mirrorBranch()
        self.rollbackToMirror()
        self.assertMasterPatchlevels(['base-0', 'patch-1'])

    def testRollbackOneRevision(self):
        """rollbackToMirror can remove the latest revision"""
        self.setUpBaseZero()
        self.mirrorBranch()
        self.setUpPatch()
        assert self.masterPatchlevels() == ['base-0', 'patch-1']
        self.rollbackToMirror()
        self.assertMasterPatchlevels(['base-0'])

    def testCommitAfterRollback(self):
        """rollbackToMirror does not prevent further commits"""
        self.testRollbackOneRevision()
        try:
            self.cleanUpTree()
            self.setUpPatch()
        except arch.ExecProblem, e:
            self.fail("CAUGHT %s" % e)
        self.assertMasterPatchlevels(['base-0', 'patch-1'])

    def testRollbackToEmptyVersion(self):
        """rollbackToMirror works when reverting to empty version"""
        self.setUpEmptyMirrorVersion()
        self.setUpBaseZero()
        self.setUpPatch()
        assert self.masterPatchlevels() == ['base-0', 'patch-1']
        self.rollbackToMirror()
        self.assertMasterPatchlevels([])

    def testRollbackToNonExistent(self):
        """rollbackToMirror works when reverting to a non existent version"""
        self.setUpBaseZero()
        self.setUpPatch()
        self.rollbackToMirror()
        versions = self.masterVersions()
        self.assertEqual([], list(versions))

    def testMirrorButNotMaster(self):
        """rollbackToMirror fails if mirror has branch but master has not"""
        self.setUpBaseZero()
        self.setUpPatch()
        self.mirrorBranch()
        self.removeMasterBranch()
        self.assertRaises(
            archivemanager.MirrorButNoMasterError,
            self.rollbackToMirror)

    def testMirrorMoreUpToDate(self):
        """rollbackToMirror fails if mirror is more up to date than master"""
        self.setUpBaseZero()
        self.setUpPatch()
        assert self.masterPatchlevels() == ['base-0', 'patch-1']
        self.mirrorBranch()
        self.rollbackToLevels(['base-0'])
        self.assertMasterPatchlevels(['base-0'])
        self.assertRaises(
            archivemanager.MirrorMoreUpToDateError,
            self.rollbackToMirror)


class TestCompareMasterToMirror(helpers.BazTreeTestCase):

    def setUp(self):
        helpers.BazTreeTestCase.setUp(self)
        self.version = self.archive_manager_helper.makeVersion()
        self.archive_manager.createMaster()
        self.archive_manager.createMirror()
        self.baz_tree_helper.setUpSigning()
        self.baz_tree_helper.setUpTree()

    def setUpBaseZero(self):
        self.baz_tree_helper.setUpBaseZero()

    def setUpPatch(self):
        self.baz_tree_helper.setUpPatch()

    def compareMasterToMirror(self, expected_old, expected_new):
        old, new = self.archive_manager.compareMasterToMirror()
        self.assertEqual(old, expected_old)
        self.assertEqual(new, expected_new)

    def testEmptyMirror(self):
        """compareMasterToMirror works with empty mirror"""
        base0 = self.version['base-0']
        patch1 = self.version['patch-1']
        patch2 = self.version['patch-2']
        self.compareMasterToMirror([], [])
        self.setUpBaseZero()
        self.compareMasterToMirror([], [base0])
        self.setUpPatch()
        self.compareMasterToMirror([], [base0, patch1])
        self.setUpPatch()
        self.compareMasterToMirror([], [base0, patch1, patch2])

    def testBase0Mirror(self):
        """compareMasterToMirror works with mirror containing base-0"""
        base0 = self.version['base-0']
        patch1 = self.version['patch-1']
        patch2 = self.version['patch-2']
        self.setUpBaseZero()
        self.mirrorBranch()
        self.compareMasterToMirror([base0], [])
        self.setUpPatch()
        self.compareMasterToMirror([base0], [patch1])
        self.setUpPatch()
        self.compareMasterToMirror([base0], [patch1, patch2])

    def testPatch1Mirror(self):
        """compareMasterToMirror works with mirror containing patch-1"""
        base0 = self.version['base-0']
        patch1 = self.version['patch-1']
        patch2 = self.version['patch-2']
        self.setUpBaseZero()
        self.setUpPatch()
        self.mirrorBranch()
        self.compareMasterToMirror([base0, patch1], [])
        self.setUpPatch()
        self.compareMasterToMirror([base0, patch1], [patch2])

    def testPatch2Mirror(self):
        """compareMasterToMirror works with mirror containing patch-2"""
        base0 = self.version['base-0']
        patch1 = self.version['patch-1']
        patch2 = self.version['patch-2']
        self.setUpBaseZero()
        self.setUpPatch()
        self.setUpPatch()
        self.mirrorBranch()
        self.compareMasterToMirror([base0, patch1, patch2], [])


class TestMirrorRevision(helpers.BazTreeTestCase):

    def setUp(self):
        helpers.BazTreeTestCase.setUp(self)
        self.version = self.archive_manager_helper.makeVersion()
        self.archive_manager.createMaster()
        self.archive_manager.createMirror()
        self.baz_tree_helper.setUpSigning()
        self.baz_tree_helper.setUpTree()
        self.baz_tree_helper.setUpBaseZero()
        self.baz_tree_helper.setUpPatch()

    def mirrorPatchLevel(self, patchlevel):
        self.archive_manager.mirrorRevision(self.version[patchlevel])

    def test(self):
        """mirrorRevision works"""
        self.assertMirrorPatchlevels([])
        self.mirrorPatchLevel('base-0')
        self.assertMirrorPatchlevels(['base-0'])
        self.mirrorPatchLevel('patch-1')
        self.assertMirrorPatchlevels(['base-0', 'patch-1'])


class TestMirrorIsEmpty(helpers.BazTreeTestCase):
    """Test cases for the mirrorNotEmpty predicate."""

    def setUp(self):
        helpers.BazTreeTestCase.setUp(self)
        self.version = self.archive_manager_helper.makeVersion()
        self.archive_manager.createMaster()

    def mirrorIsRegistered(self):
        mirror = self.archive_manager._mirror
        return mirror.is_registered()

    def mirrorVersions(self):
        mirror = self.archive_manager._mirror
        versions = self.version.archive.iter_location_versions(mirror)
        return list(versions)

    def setUpEmptyMirrorVersion(self):
        mirror = self.archive_manager._mirror
        os.mkdir(os.path.join(mirror.url, self.version.nonarch))

    def testMirrorNotRegistered(self):
        """mirrorIsEmpty is True if mirror not registered."""
        assert not self.mirrorIsRegistered()
        self.failUnless(self.archive_manager.mirrorIsEmpty())

    def testMirrorHasNoVersion(self):
        """mirrorIsEmpty is True if mirror has no version."""
        self.archive_manager.createMirror()
        assert self.mirrorIsRegistered()
        assert self.mirrorVersions() == []
        self.failUnless(self.archive_manager.mirrorIsEmpty())

    def testMirrorHasEmptyVersion(self):
        """mirrorIsEmpty is True if mirror has empty version."""
        self.archive_manager.createMirror()
        self.setUpEmptyMirrorVersion()
        assert self.mirrorVersions() == [self.version]
        assert self.mirrorPatchlevels() == []
        self.failUnless(self.archive_manager.mirrorIsEmpty())

    def testMirrorNotEmpty(self):
        """mirrorNotEmpty is True if mirror version is not empty."""
        self.archive_manager.createMirror()
        self.baz_tree_helper.setUpSigning()
        self.baz_tree_helper.setUpTree()
        self.baz_tree_helper.setUpBaseZero()
        self.mirrorBranch()
        assert self.mirrorPatchlevels() == ['base-0']
        self.failIf(self.archive_manager.mirrorIsEmpty())


TestUtil.register(__name__)
