# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Test cases for canonical.launchpad.scripts.importd.publish."""

__metaclass__ = type

__all__ = ['test_suite']


import logging
import shutil
import unittest

from bzrlib.bzrdir import BzrDir
from bzrlib.branch import Branch
from bzrlib.errors import DivergedBranches
from bzrlib.urlutils import local_path_to_url
from zope.component import getUtility

from canonical.database.sqlbase import commit
from canonical.launchpad.interfaces import (
    BranchType, IBranchSet, ILaunchpadCelebrities, IPersonSet)
from canonical.launchpad.scripts.importd.publish import (
    ensure_series_branch, ImportdPublisher, mirror_url_from_series)
from canonical.launchpad.scripts.importd.tests.helpers import ImportdTestCase


class TestImportdPublisher(ImportdTestCase):
    """Test canonical.launchpad.scripts.importd.publish.ImportdPublisher."""

    def setUp(self):
        ImportdTestCase.setUp(self)
        self.importd_publisher = ImportdPublisher(
            logging, self.sandbox.path, self.series_id,
            local_path_to_url(self.bzrmirrors))

    def assertGoodMirror(self):
        """Helper to check that the mirror branch matches expectations."""
        # the productseries.import_branch.id allows us to find the
        # mirror branch
        mirror_path = self.mirrorPath()
        mirror_control = BzrDir.open(mirror_path)
        # that branch must not have a working tree
        self.assertFalse(mirror_control.has_workingtree())
        # and its history must be the same as the branch it mirrors
        mirror_branch = mirror_control.open_branch()
        mirror_history = mirror_branch.revision_history()
        bzrworking_branch = Branch.open(self.bzrworking)
        bzrworking_history = bzrworking_branch.revision_history()
        self.assertEqual(mirror_history, bzrworking_history)

    def testInitialPublish(self):
        # Initial publishing of a vcs-import creates a Branch record, sets the
        # branch attribute of the productseries, and pushes to a branch without
        # working tree, with a name based on the branch id.
        self.setUpOneCommit()
        self.assertEqual(self.series_helper.getSeries().import_branch, None)
        self.importd_publisher.publish()
        db_branch = self.series_helper.getSeries().import_branch
        self.assertNotEqual(db_branch, None)
        self.assertGoodMirror()

    def testDivergence(self):
        # Publishing a vcs-imports branch fails if there is a divergence
        # between the local branch and the mirror.
        self.setUpOneCommit()
        # publish the branch to create the mirror and modify the productseries
        # to point to a branch
        self.importd_publisher.publish()
        # create a new bzrworking branch that diverges from the mirror
        shutil.rmtree(self.bzrworking)
        self.setUpOneCommit()
        # publish now fails
        self.assertRaises(DivergedBranches, self.importd_publisher.publish)

    def testBadBranchOwner(self):
        # Publishing an import fails if there is a branch associated with the
        # ProductSeries and its owner is not 'vcs-imports'.
        self.setUpOneCommit()
        series = self.series_helper.series
        branch = getUtility(IBranchSet).new(
            BranchType.HOSTED,
            series.name, series.product.owner, series.product.owner,
            series.product, url=None)
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        assert branch.owner != vcs_imports
        series.import_branch = branch
        commit()
        self.assertRaises(AssertionError, self.importd_publisher.publish)


class TestMirrorUrlFromSeries(ImportdTestCase):
    # mirror_url_from_series accepts an url prefix and a ProductSeries whose
    # branch is set and owned by vcs-imports. It appends the id of the branch
    # in hexadecimal form to the url prefix.

    def setUp(self):
        ImportdTestCase.setUp(self)
        self.series = self.series_helper.series
        self.sftp_prefix = 'sftp://user@host/base/'
        ensure_series_branch(self.series)

    def testSftpPrefix(self):
        # Since branches are mirrored by importd via sftp,
        # mirror_url_from_series must support sftp urls. There was once a bug
        # that made it incorrect with sftp.
        self.assertEqual(
            mirror_url_from_series(self.sftp_prefix, self.series),
            self.sftp_prefix + '%08x' % self.series.import_branch.id)

    def testSftpPrefixNoSlash(self):
        # If the prefix has no trailing slash, one should be added. It's very
        # easy to forget a trailing slash in the importd configuration.
        sftp_prefix_noslash = 'sftp://user@host/base'
        self.assertEqual(
            mirror_url_from_series(sftp_prefix_noslash, self.series),
            sftp_prefix_noslash + '/' + '%08x' % self.series.import_branch.id)

    def testNoSeriesBranch(self):
        # mirror_url_from_series checks that the series branch is set, it
        # cannot do its job otherwise, better to fail with AssertionError than
        # with AttributeError.
        assert self.series.import_branch is not None
        self.series.import_branch = None
        sftp_prefix = 'sftp://user@host/base/'
        self.assertRaises(AssertionError, mirror_url_from_series,
                          self.sftp_prefix, self.series)

    def testBadBranchValue(self):
        # mirror_url_from_series check that the series branch is owned by
        # vcs-imports and the url is None. Otherwise, the branch puller will
        # not look for the branch data on the internal vcs-import publishing
        # server.
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        assert self.series.import_branch.owner == vcs_imports
        assert self.series.import_branch.url is None
        number_one = getUtility(IPersonSet).get(1)
        assert number_one != None
        assert vcs_imports != number_one
        # First, use an improper branch owner.
        self.series.import_branch.owner = number_one
        self.assertRaises(AssertionError, mirror_url_from_series,
                          self.sftp_prefix, self.series)
        # Then use a branch with a non-NULL url.
        self.series.import_branch.owner = vcs_imports
        self.series.import_branch.url = 'http://example.com/branch'
        self.assertRaises(AssertionError, mirror_url_from_series,
                          self.sftp_prefix, self.series)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
