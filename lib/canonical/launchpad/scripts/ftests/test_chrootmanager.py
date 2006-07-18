# Copyright 2006 Canonical Ltd.  All rights reserved.
"""ChrootManager facilities tests."""

__metaclass__ = type

from unittest import TestCase, TestLoader
import os
import sys
import tempfile

from zope.component import getUtility

from canonical.config import config
from canonical.functional import ZopelessLayer
from canonical.launchpad.ftests.harness import (
    LaunchpadZopelessTestCase, LaunchpadZopelessTestSetup)

from canonical.launchpad.interfaces import IDistributionSet
from canonical.launchpad.scripts.ftpmaster import (
    ChrootManager, ChrootManagerError)

from canonical.librarian.ftests.harness import LibrarianTestSetup
from canonical.lp.dbschema import PackagePublishingPocket

class TestChrootManager(LaunchpadZopelessTestCase):
    layer = ZopelessLayer
    dbuser = 'lucille'

    def setUp(self):
        """Setup the test environment and retrieve useful instances."""
        LaunchpadZopelessTestCase.setUp(self)
        self.librarian = LibrarianTestSetup()
        self.librarian.setUp()
        self.files_to_delete = []
        self.distribution = getUtility(IDistributionSet)['ubuntu']
        self.distroarchrelease = self.distribution.currentrelease['i386']
        self.pocket = PackagePublishingPocket.SECURITY

    def tearDown(self):
        """Clean up test environment and remove the test archive."""
        self._remove_files()
        self.librarian.tearDown()
        LaunchpadZopelessTestCase.tearDown(self)

    def _create_file(self, filename, content=None):
        """Create a file in the system temporary directory.

        Annotate the path for posterior removal (see _remove_files)
        """
        filepath = os.path.join(tempfile.gettempdir(), filename)
        if content is not None:
            fd = open(filepath, "w")
            fd.write(content)
            fd.close()

        self.files_to_delete.append(filepath)
        return filepath

    def _remove_files(self):
        """Remove files during this test."""
        for filepath in self.files_to_delete:
            os.remove(filepath)

        self.files_to_delete = []

    def test_initialize(self):
        """Chroot Manager initialization"""
        chroot_manager = ChrootManager(self.distroarchrelease, self.pocket)

        self.assertEqual(self.distroarchrelease,
                         chroot_manager.distroarchrelease)
        self.assertEqual(self.pocket, chroot_manager.pocket)

    def test_add_and_get(self):
        """Adding new chroot and then retrive it."""
        chroot_manager = ChrootManager(self.distroarchrelease, self.pocket)

        chrootfilepath = self._create_file('chroot.test', content="UHMMM")
        chrootfilename = os.path.basename(chrootfilepath)

        chroot_manager.add(filepath=chrootfilepath)

        pocket_chroot = self.distroarchrelease.getChroot(self.pocket)
        self.assertEqual(chrootfilename, pocket_chroot.chroot.filename)

        # required to turn librarian results visible.
        LaunchpadZopelessTestSetup.txn.commit()

        dest = self._create_file('chroot.gotten')

        chroot_manager.get(filepath=dest)

        self.assertEqual(True, os.path.exists(dest))

    def test_update_and_remove(self):
        """Update existent chroot then remove it."""
        chroot_manager = ChrootManager(self.distroarchrelease, self.pocket)

        chrootfilepath = self._create_file('chroot.update', content="DUHHHH")
        chrootfilename = os.path.basename(chrootfilepath)

        chroot_manager.update(filepath=chrootfilepath)

        pocket_chroot = self.distroarchrelease.getChroot(self.pocket)
        self.assertEqual(chrootfilename, pocket_chroot.chroot.filename)

        # required to turn librarian results visible.
        LaunchpadZopelessTestSetup.txn.commit()

        chroot_manager.remove()

        pocket_chroot = self.distroarchrelease.getChroot(self.pocket)
        self.assertEqual(None, pocket_chroot.chroot)

    def test_remove_fail(self):
        """Attempt to remove inexistent chroot fail."""
        chroot_manager = ChrootManager(
            self.distroarchrelease, PackagePublishingPocket.RELEASE)

        self.assertRaises(
            ChrootManagerError, chroot_manager.remove)

    def test_add_fail(self):
        """Attempt to add inexistent local chroot fail."""
        chroot_manager = ChrootManager(
            self.distroarchrelease, PackagePublishingPocket.UPDATES)

        self.assertRaises(
            ChrootManagerError, chroot_manager.add, "foo-bar")


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
