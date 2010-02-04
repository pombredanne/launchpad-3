# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test source package diffs."""

__metaclass__ = type

from datetime import datetime
import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.ftests import import_public_test_keys
from lp.registry.interfaces.distribution import IDistributionSet
from lp.soyuz.interfaces.packagediff import IPackageDiffSet, PackageDiffStatus
from canonical.launchpad.testing.fakepackager import FakePackager
from canonical.launchpad.database import LibraryFileAlias
from canonical.launchpad.webapp.interfaces import (
        IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.testing import LaunchpadZopelessLayer


class TestPackageDiffs(unittest.TestCase):
    """Test package diffs."""
    layer = LaunchpadZopelessLayer
    dbuser = config.uploader.dbuser

    def setUp(self):
        """Setup proper DB connection and contents for tests

        Connect to the DB as the 'uploader' user.

        Store the `FakePackager` object used in the test uploads as `packager`
        so the tests can reuse it if necessary.
        """
        self.layer.alterConnection(dbuser='launchpad')

        fake_chroot = LibraryFileAlias.get(1)
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        warty = ubuntu.getSeries('warty')
        warty['i386'].addOrUpdateChroot(fake_chroot)

        self.layer.txn.commit()

        self.layer.alterConnection(dbuser=self.dbuser)
        self.packager = self.uploadTestPackages()
        self.layer.txn.commit()

    def uploadTestPackages(self):
        """Upload packages for testing `PackageDiff` generation.

        Upload zeca_1.0-1 and zeca_1.0-2 sources, so a `PackageDiff` between
        them is created.

        Assert there is not pending `PackageDiff` in the DB before uploading
        the package and also assert that there is one after the uploads.

        :return: the FakePackager object used to generate and upload the test,
            packages, so the tests can upload subsequent version if necessary.
        """
        # No pending PackageDiff available in sampledata.
        self.assertEqual(self.getPendingDiffs().count(), 0)

        import_public_test_keys()
        # Use FakePackager to upload a base package to ubuntu.
        packager = FakePackager(
            'zeca', '1.0', 'foo.bar@canonical.com-passwordless.sec')
        packager.buildUpstream()
        packager.buildSource()
        packager.uploadSourceVersion('1.0-1', suite="warty-updates")

        # Upload a new version of the source, so a PackageDiff can
        # be created.
        packager.buildVersion('1.0-2', changelog_text="cookies")
        packager.buildSource(include_orig=False)
        packager.uploadSourceVersion('1.0-2', suite="warty-updates")

        # Check if there is exactly one pending PackageDiff record and
        # It's the one we have just created.
        self.assertEqual(self.getPendingDiffs().count(), 1)

        return packager

    def getPendingDiffs(self):
        """Pending `PackageDiff` available."""
        return getUtility(IPackageDiffSet).getPendingDiffs()

    def test_packagediff_working(self):
        # Test the case where none of the files required for the diff are
        # expired in the librarian and where everything works as expected.
        [diff] = self.getPendingDiffs()
        self.assertEqual(0, removeSecurityProxy(diff)._countExpiredLFAs())
        diff.performDiff()
        self.assertEqual(PackageDiffStatus.COMPLETED, diff.status)

    def expireLFAsForSource(self, source, delete_as_well=True):
        """Expire the files associated with the given source package in the
        librarian."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        query = """
            UPDATE LibraryFileAlias lfa
            SET
                expires = %s
            """ % sqlvalues(datetime.utcnow())
        if delete_as_well:
            # Expire *and* delete files from librarian.
            query += """
                , content = NULL
                """
        query += """
            FROM
                SourcePackageRelease spr, SourcePackageReleaseFile sprf
            WHERE
                spr.id = %s
                AND sprf.SourcePackageRelease = spr.id
                AND sprf.libraryfile = lfa.id
            """ % sqlvalues(source.id)
        self.layer.alterConnection(dbuser='launchpad')
        result = store.execute(query)
        self.layer.txn.commit()
        self.layer.alterConnection(dbuser=self.dbuser)

    def test_packagediff_with_expired_and_deleted_lfas(self):
        # Test the case where files required for the diff are expired *and*
        # deleted in the librarian causing a package diff failure.
        [diff] = self.getPendingDiffs()
        # Expire the files associated with the 'from_source' package.
        self.expireLFAsForSource(diff.from_source)
        # The helper method now finds 3 expired files.
        self.assertEqual(3, removeSecurityProxy(diff)._countExpiredLFAs())
        diff.performDiff()
        # The diff fails due to the presence of expired files.
        self.assertEqual(PackageDiffStatus.FAILED, diff.status)

    def test_packagediff_with_expired_but_not_deleted_lfas(self):
        # Test the case where files required for the diff are expired but
        # not deleted in the librarian still allowing the package diff to be
        # performed.
        [diff] = self.getPendingDiffs()
        # Expire the files associated with the 'from_source' package.
        self.expireLFAsForSource(diff.from_source, delete_as_well=False)
        # The helper method now finds no expired files.
        self.assertEqual(0, removeSecurityProxy(diff)._countExpiredLFAs())
        diff.performDiff()
        # The diff succeeds as expected.
        self.assertEqual(PackageDiffStatus.COMPLETED, diff.status)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
