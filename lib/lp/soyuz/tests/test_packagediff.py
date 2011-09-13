# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test source package diffs."""

__metaclass__ = type

from datetime import datetime

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.soyuz.enums import PackageDiffStatus
from lp.soyuz.tests.soyuz import TestPackageDiffsBase
from lp.testing.dbuser import dbuser


class TestPackageDiffs(TestPackageDiffsBase):
    """Test package diffs."""
    layer = LaunchpadZopelessLayer
    dbuser = config.uploader.dbuser

    def test_packagediff_working(self):
        # Test the case where none of the files required for the diff are
        # expired in the librarian and where everything works as expected.
        [diff] = self.getPendingDiffs()
        self.assertEqual(0, removeSecurityProxy(diff)._countDeletedLFAs())
        diff.performDiff()
        self.assertEqual(PackageDiffStatus.COMPLETED, diff.status)

    def expireLFAsForSource(self, source, expire=True, delete=True):
        """Expire the files associated with the given source package in the
        librarian."""
        assert expire or delete
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        query = """
            UPDATE LibraryFileAlias lfa
            SET
            """
        if expire:
            query += "expires = %s" % sqlvalues(datetime.utcnow())
        if expire and delete:
            query += ", "
        if delete:
            query += "content = NULL"
        query += """
            FROM
                SourcePackageRelease spr, SourcePackageReleaseFile sprf
            WHERE
                spr.id = %s
                AND sprf.SourcePackageRelease = spr.id
                AND sprf.libraryfile = lfa.id
            """ % sqlvalues(source.id)
        with dbuser('launchpad'):
            store.execute(query)

    def test_packagediff_with_expired_and_deleted_lfas(self):
        # Test the case where files required for the diff are expired *and*
        # deleted in the librarian causing a package diff failure.
        [diff] = self.getPendingDiffs()
        # Expire and delete the files associated with the 'from_source'
        # package.
        self.expireLFAsForSource(diff.from_source)
        # The helper method now finds 3 expired files.
        self.assertEqual(3, removeSecurityProxy(diff)._countDeletedLFAs())
        diff.performDiff()
        # The diff fails due to the presence of expired files.
        self.assertEqual(PackageDiffStatus.FAILED, diff.status)

    def test_packagediff_with_expired_but_not_deleted_lfas(self):
        # Test the case where files required for the diff are expired but
        # not deleted in the librarian still allowing the package diff to be
        # performed.
        [diff] = self.getPendingDiffs()
        # Expire but don't delete the files associated with the 'from_source'
        # package.
        self.expireLFAsForSource(diff.from_source, expire=True, delete=False)
        # The helper method now finds no expired files.
        self.assertEqual(0, removeSecurityProxy(diff)._countDeletedLFAs())
        diff.performDiff()
        # The diff succeeds as expected.
        self.assertEqual(PackageDiffStatus.COMPLETED, diff.status)

    def test_packagediff_with_deleted_but_not_expired_lfas(self):
        # Test the case where files required for the diff have been
        # deleted explicitly, not through expiry.
        [diff] = self.getPendingDiffs()
        # Delete the files associated with the 'from_source' package.
        self.expireLFAsForSource(diff.from_source, expire=False, delete=True)
        # The helper method now finds 3 expired files.
        self.assertEqual(3, removeSecurityProxy(diff)._countDeletedLFAs())
        diff.performDiff()
        # The diff fails due to the presence of expired files.
        self.assertEqual(PackageDiffStatus.FAILED, diff.status)
