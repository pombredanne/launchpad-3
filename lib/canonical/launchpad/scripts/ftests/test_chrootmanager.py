# Copyright 2006 Canonical Ltd.  All rights reserved.
"""ChrootManager facilities tests."""

__metaclass__ = type

from unittest import TestCase, TestLoader
import os
import tempfile

from zope.component import getUtility

from canonical.database.sqlbase import commit
from canonical.launchpad.interfaces import IDistributionSet
from canonical.launchpad.scripts.ftpmaster import (
    ChrootManager, ChrootManagerError)
from canonical.lp.dbschema import PackagePublishingPocket
from canonical.testing import LaunchpadZopelessLayer

class TestChrootManager(TestCase):
    layer = LaunchpadZopelessLayer
    dbuser = 'lucille'

    def setUp(self):
        """Setup the test environment and retrieve useful instances."""
        self.files_to_delete = []
        self.distribution = getUtility(IDistributionSet)['ubuntu']
        self.distroarchseries = self.distribution.currentseries['i386']

    def tearDown(self):
        """Clean up test environment and remove the test archive."""
        self._remove_files()

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
        chroot_manager = ChrootManager(self.distroarchseries)

        self.assertEqual(self.distroarchseries,
                         chroot_manager.distroarchseries)
        self.assertEqual([], chroot_manager._messages)

    def test_add_and_get(self):
        """Adding new chroot and then retrive it."""
        chrootfilepath = self._create_file('chroot.test', content="UHMMM")
        chrootfilename = os.path.basename(chrootfilepath)

        chroot_manager = ChrootManager(
            self.distroarchseries, filepath=chrootfilepath)

        chroot_manager.add()
        self.assertEqual(
            ["LibraryFileAlias: 75, 5 bytes, 5088e6471ab02d4268002f529a02621c",
             "PocketChroot for 'The Hoary Hedgehog Release for i386 (x86)' "
             "(1) added."], chroot_manager._messages)

        pocket_chroot = self.distroarchseries.getPocketChroot()
        self.assertEqual(chrootfilename, pocket_chroot.chroot.filename)

        # required to turn librarian results visible.
        commit()

        dest = self._create_file('chroot.gotten')

        chroot_manager = ChrootManager(
            self.distroarchseries, filepath=dest)

        chroot_manager.get()
        self.assertEqual(
            ["PocketChroot for 'The Hoary Hedgehog Release for i386 (x86)' "
             "(1) retrieved.",
             "Writing to '/tmp/chroot.gotten'."], chroot_manager._messages)

        self.assertEqual(True, os.path.exists(dest))

    def test_update_and_remove(self):
        """Update existing chroot then remove it."""
        chrootfilepath = self._create_file('chroot.update', content="DUHHHH")
        chrootfilename = os.path.basename(chrootfilepath)

        chroot_manager = ChrootManager(
            self.distroarchseries, filepath=chrootfilepath)

        chroot_manager.update()
        self.assertEqual(
            ["LibraryFileAlias: 75, 6 bytes, a4cd43e083161afcdf26f4324024d8ef",
             "PocketChroot for 'The Hoary Hedgehog Release for i386 (x86)' "
             "(1) updated."], chroot_manager._messages)

        pocket_chroot = self.distroarchseries.getPocketChroot()
        self.assertEqual(chrootfilename, pocket_chroot.chroot.filename)

        # required to turn librarian results visible.
        commit()

        chroot_manager = ChrootManager(self.distroarchseries)

        chroot_manager.remove()
        self.assertEqual(
            ["PocketChroot for 'The Hoary Hedgehog Release for i386 (x86)' "
             "(1) retrieved.",
             "PocketChroot for 'The Hoary Hedgehog Release for i386 (x86)' "
             "(1) removed."], chroot_manager._messages)

        pocket_chroot = self.distroarchseries.getPocketChroot()
        self.assertEqual(None, pocket_chroot.chroot)

    def test_remove_fail(self):
        """Attempt to remove non-existent chroot will fail."""
        # Use a different distroarchseries in the sample data; this one
        # has no chroot.
        distroarchseries = self.distribution['warty']['hppa']
        chroot_manager = ChrootManager(distroarchseries)

        self.assertRaises(
            ChrootManagerError, chroot_manager.remove)

    def test_add_fail(self):
        """Attempt to add non-existent local chroot will fail."""
        chroot_manager = ChrootManager(
            self.distroarchseries,
            filepath='foo-bar')

        self.assertRaises(
            ChrootManagerError, chroot_manager.add)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
