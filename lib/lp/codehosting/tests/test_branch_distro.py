# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""XXX write me."""

__metaclass__ = type

import re
from StringIO import StringIO
import unittest

from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir
from bzrlib.errors import NotStacked
from bzrlib.tests import TestCaseWithTransport
from bzrlib.transport import get_transport
from bzrlib.transport.chroot import ChrootServer

import transaction

from canonical.testing.layers import ZopelessAppServerLayer
from canonical.launchpad.scripts.logger import FakeLogger, QuietFakeLogger

from lp.codehosting.branch_distro import (
    DistroBrancher, switch_branches)
from lp.codehosting.vfs import branch_id_to_path
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.testing import TestCaseWithFactory

RELEASE = PackagePublishingPocket.RELEASE


class FakeBranch:
    def __init__(self, id):
        self.id = id
    @property
    def unique_name(self):
        return branch_id_to_path(self.id)


class TestSwitchBranches(TestCaseWithTransport):
    """XXX."""

    def test_switch_branches(self):

        chroot_server = ChrootServer(self.get_transport())
        chroot_server.setUp()
        self.addCleanup(chroot_server.tearDown)
        scheme = chroot_server.get_url()

        old_branch = FakeBranch(1)
        self.get_transport(old_branch.unique_name).create_prefix()
        tree = self.make_branch_and_tree(old_branch.unique_name)
        tree.commit(message='.')

        new_branch = FakeBranch(2)

        switch_branches('.', scheme, old_branch, new_branch)

        # Post conditions:
        # 1. unstacked branch in new_branch's location
        # 2. stacked branch with no revisions in repo at old_branch
        # 3. last_revision() the same for two branches

        old_location_bzrdir = BzrDir.open(scheme + old_branch.unique_name)
        new_location_bzrdir = BzrDir.open(scheme + new_branch.unique_name)

        old_location_branch = old_location_bzrdir.open_branch()
        new_location_branch = new_location_bzrdir.open_branch()

        # 1. unstacked branch in new_branch's location
        #print new_location_branch.get_stacked_on_url()
        self.assertRaises(NotStacked, new_location_branch.get_stacked_on_url)

        # 2. stacked branch with no revisions in repo at old_branch
        self.assertEqual(
            '/' + new_branch.unique_name,
            old_location_branch.get_stacked_on_url())
        self.assertEqual(
            [], old_location_bzrdir.open_repository().all_revision_ids())

        # 3. last_revision() the same for two branches
        self.assertEqual(
            old_location_branch.last_revision(),
            new_location_branch.last_revision())


class TestDistroBrancher(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.useBzrBranches(real_server=True)

    def makeOfficialPackageBranch(self, distroseries=None):
        """Make an official package branch with an underlying bzr branch.

        XXX.
        """
        db_branch = self.factory.makePackageBranch(distroseries=distroseries)
        db_branch.sourcepackage.setBranch(RELEASE, db_branch, db_branch.owner)

        transaction.commit()

        _, tree = self.create_branch_and_tree(
            tree_location=self.factory.getUniqueString(), db_branch=db_branch,
            hosted=True)
        tree.commit('')
        mirrored_branch = BzrDir.create_branch_convenience(
            db_branch.warehouse_url)
        mirrored_branch.pull(tree.branch)

        return db_branch

    def test_clone_branch(self):

        db_branch = self.makeOfficialPackageBranch()

        new_distro_series = self.factory.makeDistroRelease(
            distribution=db_branch.distribution)

        brancher = DistroBrancher(
            QuietFakeLogger(), db_branch.distroseries, new_distro_series)
        brancher.makeOneNewBranch(db_branch)

        new_sourcepackage = new_distro_series.getSourcePackage(
            db_branch.sourcepackage.name)
        new_branch = new_sourcepackage.getBranch(RELEASE)

        self.assertIsNot(new_branch, None)

    def test_branch_distro(self):

        db_branch = self.makeOfficialPackageBranch()
        db_branch2 = self.makeOfficialPackageBranch(
            distroseries=db_branch.distroseries)

        new_distro_series = self.factory.makeDistroRelease(
            distribution=db_branch.distribution)

        brancher = DistroBrancher(
            QuietFakeLogger(), db_branch.distroseries, new_distro_series)

        brancher.makeNewBranches()

        new_sourcepackage = new_distro_series.getSourcePackage(
            db_branch.sourcepackage.name)
        new_branch = new_sourcepackage.getBranch(RELEASE)
        new_sourcepackage2 = new_distro_series.getSourcePackage(
            db_branch2.sourcepackage.name)
        new_branch2 = new_sourcepackage2.getBranch(RELEASE)

        self.assertIsNot(new_branch, None)
        self.assertIsNot(new_branch2, None)

    def makeNewSeriesAndBrancher(self, db_branch):
        self._log_file = StringIO()
        new_distro_series = self.factory.makeDistroRelease(
            distribution=db_branch.distribution, name='new')
        return DistroBrancher(
            FakeLogger(self._log_file), db_branch.distroseries,
            new_distro_series)

    def clearLogMessages(self):
        self._log_file.seek(0, 0)
        self._log_file.truncate()

    def assertLogMessages(self, patterns):
        """ """
        log_messages = self._log_file.getvalue().splitlines()
        if len(log_messages) > len(patterns):
            self.fail(
                "More log messages (%s) than expected (%s)" %
                (log_messages, patterns))
        elif len(log_messages) < len(patterns):
            self.fail(
                "Fewer log messages (%s) than expected (%s)" %
                (log_messages, patterns))
        for pattern, message in zip(patterns, log_messages):
            if not re.match(pattern, message):
                self.fail("%r does not match %r" % (pattern, message))

    def test_makeNewBranch_checks_ok(self):
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch)
        brancher.makeOneNewBranch(db_branch)
        self.clearLogMessages()
        ok = brancher.checkOneBranch(db_branch)
        self.assertLogMessages([])
        self.assertTrue(ok)

    def test_checkOneBranch_no_official_branch(self):
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch)
        ok = brancher.checkOneBranch(db_branch)
        self.assertFalse(ok)
        self.assertLogMessages(
            ['^WARNING No official branch found for .*/.*/.*$'])

    def test_checkOneBranch_new_hosted_branch_missing(self):
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch)
        new_db_branch = brancher.makeOneNewBranch(db_branch)
        get_transport(new_db_branch.getPullURL()).delete_tree('.bzr')
        ok = brancher.checkOneBranch(db_branch)
        self.assertFalse(ok)
        # Deleting the new hosted branch will break the old branch, as that's
        # stacked on the new one.
        self.assertLogMessages([
            '^WARNING No bzr branch at new location '
            'lp-hosted:///.*/.*/.*/.*$',
            '^WARNING No bzr branch at old location '
            'lp-hosted:///.*/.*/.*/.*$',
            ])

    def test_checkOneBranch_new_mirrored_branch_missing(self):
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch)
        new_db_branch = brancher.makeOneNewBranch(db_branch)
        get_transport(new_db_branch.warehouse_url).delete_tree('.bzr')
        ok = brancher.checkOneBranch(db_branch)
        self.assertFalse(ok)
        # Deleting the new mirrored branch will break the old branch, as that's
        # stacked on the new one.
        self.assertLogMessages([
            '^WARNING No bzr branch at new location '
            'lp-mirrored:///.*/.*/.*/.*$',
            '^WARNING No bzr branch at old location '
            'lp-mirrored:///.*/.*/.*/.*$',
            ])

    def test_checkOneBranch_old_hosted_branch_missing(self):
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch)
        brancher.makeOneNewBranch(db_branch)
        get_transport(db_branch.getPullURL()).delete_tree('.bzr')
        ok = brancher.checkOneBranch(db_branch)
        self.assertFalse(ok)
        self.assertLogMessages([
            '^WARNING No bzr branch at old location '
            'lp-hosted:///.*/.*/.*/.*$',
            ])

    def test_checkOneBranch_old_mirrored_branch_missing(self):
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch)
        brancher.makeOneNewBranch(db_branch)
        get_transport(db_branch.warehouse_url).delete_tree('.bzr')
        ok = brancher.checkOneBranch(db_branch)
        self.assertFalse(ok)
        self.assertLogMessages([
            '^WARNING No bzr branch at old location '
            'lp-mirrored:///.*/.*/.*/.*$',
            ])

    def test_checkOneBranch_new_hosted_stacked(self):
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch)
        new_db_branch = brancher.makeOneNewBranch(db_branch)
        b, _ = self.create_branch_and_tree(
            self.factory.getUniqueString(), hosted=True)
        Branch.open(new_db_branch.getPullURL()).set_stacked_on_url(
            '/' + b.unique_name)
        ok = brancher.checkOneBranch(db_branch)
        self.assertFalse(ok)
        self.assertLogMessages([
            '^WARNING New branch at lp-hosted:///.*/.*/.*/.* is stacked on '
            '/.*/.*/.*, should be unstacked.$',
            ])

    def test_checkOneBranch_new_mirrored_stacked(self):
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch)
        new_db_branch = brancher.makeOneNewBranch(db_branch)
        b, _ = self.create_branch_and_tree(
            self.factory.getUniqueString(), hosted=False)
        Branch.open(new_db_branch.warehouse_url).set_stacked_on_url(
            '/' + b.unique_name)
        ok = brancher.checkOneBranch(db_branch)
        self.assertFalse(ok)
        self.assertLogMessages([
            '^WARNING New branch at lp-mirrored:///.*/.*/.*/.* is stacked on '
            '/.*/.*/.*, should be unstacked.$',
            ])

    def test_checkOneBranch_old_hosted_unstacked(self):
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch)
        brancher.makeOneNewBranch(db_branch)
        old_hosted_bzr_branch = Branch.open(db_branch.getPullURL())
        old_hosted_bzr_branch.set_stacked_on_url(None)
        ok = brancher.checkOneBranch(db_branch)
        self.assertLogMessages([
            '^WARNING Old branch at lp-hosted:///.*/.*/.*/.* is not '
            'stacked, should be stacked on /.*/.*/.*.$',
            '^.*has .* revisions.*$',
            ])
        self.assertFalse(ok)

    def test_checkOneBranch_old_mirrored_unstacked(self):
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch)
        brancher.makeOneNewBranch(db_branch)
        old_mirrored_bzr_branch = Branch.open(db_branch.warehouse_url)
        old_mirrored_bzr_branch.set_stacked_on_url(None)
        ok = brancher.checkOneBranch(db_branch)
        self.assertLogMessages([
            '^WARNING Old branch at lp-mirrored:///.*/.*/.*/.* is not '
            'stacked, should be stacked on /.*/.*/.*.$',
            '^.*has .* revisions.*$',
            ])
        self.assertFalse(ok)

    def test_checkOneBranch_old_hosted_misstacked(self):
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch)
        brancher.makeOneNewBranch(db_branch)
        b, _ = self.create_branch_and_tree(
            self.factory.getUniqueString(), hosted=True)
        Branch.open(db_branch.getPullURL()).set_stacked_on_url(
            '/' + b.unique_name)
        ok = brancher.checkOneBranch(db_branch)
        self.assertLogMessages([
            '^WARNING Old branch at lp-hosted:///.*/.*/.*/.* is stacked on '
            '/.*/.*/.*, should be stacked on /.*/.*/.*.$',
            ])
        self.assertFalse(ok)

    def test_checkOneBranch_old_mirrored_misstacked(self):
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch)
        brancher.makeOneNewBranch(db_branch)
        b, _ = self.create_branch_and_tree(
            self.factory.getUniqueString(), hosted=False)
        Branch.open(db_branch.warehouse_url).set_stacked_on_url(
            '/' + b.unique_name)
        ok = brancher.checkOneBranch(db_branch)
        self.assertLogMessages([
            '^WARNING Old branch at lp-mirrored:///.*/.*/.*/.* is stacked on '
            '/.*/.*/.*, should be stacked on /.*/.*/.*.$',
            ])
        self.assertFalse(ok)

    def test_checkOneBranch_old_hosted_has_revisions(self):
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch)
        brancher.makeOneNewBranch(db_branch)
        old_hosted_bzr_branch = Branch.open(db_branch.getPullURL())
        old_hosted_bzr_branch.create_checkout(
            self.factory.getUniqueString()).commit('')
        ok = brancher.checkOneBranch(db_branch)
        self.assertLogMessages([
            '^WARNING Repository at lp-hosted:///.*/.*/.*/.* has 1 revisions.'
            ])
        self.assertFalse(ok)

    def test_checkOneBranch_old_mirrored_has_revisions(self):
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch)
        brancher.makeOneNewBranch(db_branch)
        old_mirrored_bzr_branch = Branch.open(db_branch.warehouse_url)
        old_mirrored_bzr_branch.create_checkout(
            self.factory.getUniqueString()).commit('')
        ok = brancher.checkOneBranch(db_branch)
        self.assertLogMessages([
            '^WARNING Repository at lp-mirrored:///.*/.*/.*/.* has 1 '
            'revisions.'
            ])
        self.assertFalse(ok)

    def test_checkOneBranch_old_hosted_has_null_tip(self):
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch)
        brancher.makeOneNewBranch(db_branch)
        old_hosted_bzr_branch = Branch.open(db_branch.getPullURL())
        old_hosted_bzr_branch.set_last_revision_info(0, 'null:')
        ok = brancher.checkOneBranch(db_branch)
        self.assertLogMessages([
            '^WARNING Old branch at lp-hosted:///.*/.*/.*/.* has null tip '
            'revision.'
            ])
        self.assertFalse(ok)

    def test_checkOneBranch_old_mirrored_has_null_tip(self):
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch)
        brancher.makeOneNewBranch(db_branch)
        old_mirrored_bzr_branch = Branch.open(db_branch.warehouse_url)
        old_mirrored_bzr_branch.set_last_revision_info(0, 'null:')
        ok = brancher.checkOneBranch(db_branch)
        self.assertLogMessages([
            '^WARNING Old branch at lp-mirrored:///.*/.*/.*/.* has null tip '
            'revision.'
            ])
        self.assertFalse(ok)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

