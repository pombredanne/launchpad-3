# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for making new source package branches just after a distro release.
"""

__metaclass__ = type

import os
import re
from StringIO import StringIO
from subprocess import PIPE, Popen, STDOUT
import textwrap
import unittest

from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir
from bzrlib.errors import NotStacked
from bzrlib.tests import TestCaseWithTransport
from bzrlib.transport import get_transport
from bzrlib.transport.chroot import ChrootServer

from lazr.uri import URI

import transaction

from canonical.config import config
from canonical.testing.layers import ZopelessAppServerLayer
from canonical.launchpad.scripts.logger import FakeLogger, QuietFakeLogger

from lp.codehosting.branchdistro import DistroBrancher, switch_branches
from lp.codehosting.vfs import branch_id_to_path
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.testing import TestCaseWithFactory


# We say "RELEASE" often enough to not want to say "PackagePublishingPocket."
# each time.
RELEASE = PackagePublishingPocket.RELEASE


class FakeBranch:
    """Just enough of a Branch to pass `test_switch_branches`."""

    def __init__(self, id):
        self.id = id

    @property
    def unique_name(self):
        return branch_id_to_path(self.id)


class TestSwitchBranches(TestCaseWithTransport):
    """Tests for `switch_branches`."""

    def test_switch_branches(self):
        # switch_branches moves a branch to the new location and places a
        # branch (with no revisions) stacked on the new branch in the old
        # location.

        chroot_server = ChrootServer(self.get_transport())
        chroot_server.setUp()
        self.addCleanup(chroot_server.tearDown)
        scheme = chroot_server.get_url().rstrip('/:')

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

        old_location_bzrdir = BzrDir.open(str(URI(
            scheme=scheme, host='', path='/' + old_branch.unique_name)))
        new_location_bzrdir = BzrDir.open(str(URI(
            scheme=scheme, host='', path='/' + new_branch.unique_name)))

        old_location_branch = old_location_bzrdir.open_branch()
        new_location_branch = new_location_bzrdir.open_branch()

        # 1. unstacked branch in new_branch's location
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
    """Tests for `DistroBrancher`."""

    layer = ZopelessAppServerLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.useBzrBranches(real_server=True)

    def makeOfficialPackageBranch(self, distroseries=None):
        """Make an official package branch with an underlying bzr branch."""
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

    def makeNewSeriesAndBrancher(self, distroseries=None):
        """Make a DistroBrancher.

        Any messages logged by this DistroBrancher can be checked by calling
        `assertLogMessages` below.
        """
        if distroseries is None:
            distroseries = self.factory.makeDistroRelease()
        self._log_file = StringIO()
        new_distroseries = self.factory.makeDistroRelease(
            distribution=distroseries.distribution, name='new')
        transaction.commit()
        self.layer.switchDbUser('branch-distro')
        return DistroBrancher(
            FakeLogger(self._log_file), distroseries, new_distroseries)

    def clearLogMessages(self):
        """Forget about all logged messages seen so far."""
        self._log_file.seek(0, 0)
        self._log_file.truncate()

    def assertLogMessages(self, patterns):
        """Assert that the messages logged meet expectations.

        :param patterns: A list of regular expressions.  The length must match
            the number of messages logged, and then each pattern must match
            the messages logged in order.
        """
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

    def test_DistroBrancher_same_distro_check(self):
        # DistroBrancher.__init__ raises AssertionError if the two
        # distroseries passed are not from the same distribution.
        self.assertRaises(
            AssertionError, DistroBrancher, None,
            self.factory.makeDistroRelease(),
            self.factory.makeDistroRelease())

    def test_DistroBrancher_same_distroseries_check(self):
        # DistroBrancher.__init__ raises AssertionError if passed the same
        # distroseries twice.
        distroseries = self.factory.makeDistroRelease()
        self.assertRaises(
            AssertionError, DistroBrancher, None, distroseries, distroseries)

    def test_fromNames(self):
        # DistroBrancher.fromNames constructs a DistroBrancher from the names
        # of a distribution and two distroseries within it.
        distribution = self.factory.makeDistribution()
        distroseries1 = self.factory.makeDistroRelease(
            distribution=distribution)
        distroseries2 = self.factory.makeDistroRelease(
            distribution=distribution)
        brancher = DistroBrancher.fromNames(
            None, distribution.name, distroseries1.name, distroseries2.name)
        self.assertEqual(
            [distroseries1, distroseries2],
            [brancher.old_distroseries, brancher.new_distroseries])

    # A word on testing strategy: we don't directly test the post conditions
    # of makeOneNewBranch, but we do test that it satisfies checkOneBranch and
    # the tests for checkOneBranch verify that this function rejects various
    # ways in which makeOneNewBranch could conceivably fail.

    def test_makeOneNewBranch(self):
        # makeOneNewBranch creates an official package branch in the new
        # distroseries.
        db_branch = self.makeOfficialPackageBranch()

        brancher = self.makeNewSeriesAndBrancher(db_branch.distroseries)
        brancher.makeOneNewBranch(db_branch)

        new_branch = brancher.new_distroseries.getSourcePackage(
            db_branch.sourcepackage.name).getBranch(RELEASE)

        self.assertIsNot(None, new_branch)
        # The branch owner/name/target is the same, apart from the
        # distroseries.
        self.assertEqual(
            [db_branch.owner, db_branch.distribution,
             db_branch.sourcepackagename, db_branch.name],
            [new_branch.owner, new_branch.distribution,
             new_branch.sourcepackagename, new_branch.name])

    def test_makeOneNewBranch_inconsistent_branch(self):
        # makeOneNewBranch skips over an inconsistent official package branch
        # (see `checkConsistentOfficialPackageBranch` for precisely what an
        # "inconsistent official package branch" is).
        unofficial_branch = self.factory.makePackageBranch()
        brancher = self.makeNewSeriesAndBrancher(
            unofficial_branch.distroseries)
        brancher.makeOneNewBranch(unofficial_branch)

        new_branch = brancher.new_distroseries.getSourcePackage(
            unofficial_branch.sourcepackage.name).getBranch(RELEASE)
        self.assertIs(None, new_branch)
        self.assertLogMessages(
            ['^WARNING .* is not an official branch$',
             '^WARNING Skipping branch$'])

    def test_makeNewBranches(self):
        # makeNewBranches calls makeOneNewBranch for each official branch in
        # the old distroseries.
        db_branch = self.makeOfficialPackageBranch()
        db_branch2 = self.makeOfficialPackageBranch(
            distroseries=db_branch.distroseries)

        new_distroseries = self.factory.makeDistroRelease(
            distribution=db_branch.distribution)

        brancher = DistroBrancher(
            QuietFakeLogger(), db_branch.distroseries, new_distroseries)

        brancher.makeNewBranches()

        new_sourcepackage = new_distroseries.getSourcePackage(
            db_branch.sourcepackage.name)
        new_branch = new_sourcepackage.getBranch(RELEASE)
        new_sourcepackage2 = new_distroseries.getSourcePackage(
            db_branch2.sourcepackage.name)
        new_branch2 = new_sourcepackage2.getBranch(RELEASE)

        self.assertIsNot(None, new_branch)
        self.assertIsNot(None, new_branch2)

    def test_makeNewBranches_idempotent(self):
        # makeNewBranches is idempotent in the sense that if a branch in the
        # old distroseries already has a counterpart in the new distroseries,
        # it is silently ignored.
        db_branch = self.makeOfficialPackageBranch()

        brancher = self.makeNewSeriesAndBrancher(db_branch.distroseries)
        brancher.makeNewBranches()
        brancher.makeNewBranches()

        new_branch = brancher.new_distroseries.getSourcePackage(
            db_branch.sourcepackage.name).getBranch(RELEASE)

        self.assertIsNot(new_branch, None)

    def test_makeOneNewBranch_checks_ok(self):
        # After calling makeOneNewBranch for a branch, calling checkOneBranch
        # returns True for that branch.
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch.distroseries)
        brancher.makeOneNewBranch(db_branch)
        self.clearLogMessages()
        ok = brancher.checkOneBranch(db_branch)
        self.assertLogMessages([])
        self.assertTrue(ok)

    def test_checkConsistentOfficialPackageBranch_product_branch(self):
        # checkConsistentOfficialPackageBranch returns False when passed a
        # product branch.
        db_branch = self.factory.makeProductBranch()
        brancher = self.makeNewSeriesAndBrancher()
        ok = brancher.checkConsistentOfficialPackageBranch(db_branch)
        self.assertLogMessages([
            '^WARNING Encountered unexpected product branch .*/.*/.*$'])
        self.assertFalse(ok)

    def test_checkConsistentOfficialPackageBranch_personal_branch(self):
        # checkConsistentOfficialPackageBranch returns False when passed a
        # personal branch.
        db_branch = self.factory.makePersonalBranch()
        brancher = self.makeNewSeriesAndBrancher()
        ok = brancher.checkConsistentOfficialPackageBranch(db_branch)
        self.assertLogMessages([
            '^WARNING Encountered unexpected personal branch .*/.*/.*$'])
        self.assertFalse(ok)

    def test_checkConsistentOfficialPackageBranch_no_official_branch(self):
        # checkConsistentOfficialPackageBranch returns False when passed a
        # branch which is not official for any package.
        db_branch = self.factory.makePackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch.distroseries)
        ok = brancher.checkConsistentOfficialPackageBranch(db_branch)
        self.assertLogMessages(
            ['^WARNING .*/.*/.* is not an official branch$'])
        self.assertFalse(ok)

    def test_checkConsistentOfficialPackageBranch_official_elsewhere(self):
        # checkConsistentOfficialPackageBranch returns False when passed a
        # branch which is official for a sourcepackage that it is not a branch
        # for.
        db_branch = self.factory.makePackageBranch()
        self.factory.makeSourcePackage().setBranch(
            RELEASE, db_branch, db_branch.owner)
        brancher = self.makeNewSeriesAndBrancher(db_branch.distroseries)
        ok = brancher.checkConsistentOfficialPackageBranch(db_branch)
        self.assertLogMessages(
            ['^WARNING .*/.*/.* is the official branch for .*/.*/.* but not '
             'its sourcepackage$'])
        self.assertFalse(ok)

    def test_checkConsistentOfficialPackageBranch_official_twice(self):
        # checkConsistentOfficialPackageBranch returns False when passed a
        # branch that is official for two sourcepackages.
        db_branch = self.factory.makePackageBranch()
        db_branch.sourcepackage.setBranch(RELEASE, db_branch, db_branch.owner)
        self.factory.makeSourcePackage().setBranch(
            RELEASE, db_branch, db_branch.owner)
        brancher = self.makeNewSeriesAndBrancher(db_branch.distroseries)
        ok = brancher.checkConsistentOfficialPackageBranch(db_branch)
        self.assertLogMessages([
            '^WARNING .*/.*/.* is official for multiple series: .*/.*/.*, '
            '.*/.*/.*$'])
        self.assertFalse(ok)

    def test_checkConsistentOfficialPackageBranch_ok(self):
        # checkConsistentOfficialPackageBranch returns True when passed a
        # branch that is official for its sourcepackage and no other.
        db_branch = self.factory.makePackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch.distroseries)
        db_branch.sourcepackage.setBranch(RELEASE, db_branch, db_branch.owner)
        ok = brancher.checkConsistentOfficialPackageBranch(db_branch)
        self.assertLogMessages([])
        self.assertTrue(ok)

    def test_checkOneBranch_inconsistent_old_package_branch(self):
        # checkOneBranch returns False when passed a branch that is not a
        # consistent official package branch.
        db_branch = self.factory.makePackageBranch()
        brancher = self.makeNewSeriesAndBrancher()
        ok = brancher.checkOneBranch(db_branch)
        self.assertFalse(ok)
        self.assertLogMessages(
            ['^WARNING .*/.*/.* is not an official branch$'])

    def test_checkOneBranch_no_new_official_branch(self):
        # checkOneBranch returns False when there is no corresponding official
        # package branch in the new distroseries.
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch.distroseries)
        ok = brancher.checkOneBranch(db_branch)
        self.assertFalse(ok)
        self.assertLogMessages(
            ['^WARNING No official branch found for .*/.*/.*$'])

    def test_checkOneBranch_inconsistent_new_package_branch(self):
        # checkOneBranch returns False when the corresponding official package
        # branch in the new distroseries is not consistent.
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch.distroseries)
        new_db_branch = brancher.makeOneNewBranch(db_branch)
        self.layer.switchDbUser('launchpad')
        new_db_branch.setTarget(
            new_db_branch.owner,
            source_package=self.factory.makeSourcePackage())
        transaction.commit()
        self.layer.switchDbUser('branch-distro')
        ok = brancher.checkOneBranch(new_db_branch)
        self.assertFalse(ok)
        self.assertLogMessages(
            ['^WARNING .*/.*/.* is the official branch for .*/.*/.* but not '
             'its sourcepackage$'])

    def checkOneBranch_new_branch_missing(self, branch_type):
        # checkOneBranch returns False when there is no bzr branch for the
        # database branch in the new distroseries.
        assert branch_type in ('hosted', 'mirrored')
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch.distroseries)
        new_db_branch = brancher.makeOneNewBranch(db_branch)
        if branch_type == 'hosted':
            url = new_db_branch.getPullURL()
        else:
            url = new_db_branch.warehouse_url
        get_transport(url).delete_tree('.bzr')
        ok = brancher.checkOneBranch(db_branch)
        self.assertFalse(ok)
        # Deleting the new branch will break the old branch, as that's stacked
        # on the new one.
        self.assertLogMessages([
            '^WARNING No bzr branch at new location lp-%s:///.*/.*/.*/.*$'
            % branch_type,
            '^WARNING No bzr branch at old location lp-%s:///.*/.*/.*/.*$'
            % branch_type,
            ])

    def test_checkOneBranch_new_hosted_branch_missing(self):
        # checkOneBranch returns False when there is no bzr branch in the
        # hosted area for the database branch in the new distroseries.
        self.checkOneBranch_new_branch_missing('hosted')

    def test_checkOneBranch_new_mirrored_branch_missing(self):
        # checkOneBranch returns False when there is no bzr branch in the
        # mirrored area for the database branch in the new distroseries.
        self.checkOneBranch_new_branch_missing('mirrored')

    def checkOneBranch_old_branch_missing(self, branch_type):
        # checkOneBranch returns False when there is no bzr branchfor the
        # database branch in old distroseries.
        assert branch_type in ('hosted', 'mirrored')
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch.distroseries)
        brancher.makeOneNewBranch(db_branch)
        if branch_type == 'hosted':
            url = db_branch.getPullURL()
        else:
            url = db_branch.warehouse_url
        get_transport(url).delete_tree('.bzr')
        ok = brancher.checkOneBranch(db_branch)
        self.assertFalse(ok)
        self.assertLogMessages([
            '^WARNING No bzr branch at old location lp-%s:///.*/.*/.*/.*$'
            % branch_type,
            ])

    def test_checkOneBranch_old_hosted_branch_missing(self):
        # checkOneBranch returns False when there is no bzr branch in the
        # hosted area for the database branch in old distroseries.
        self.checkOneBranch_old_branch_missing('hosted')

    def test_checkOneBranch_old_mirrored_branch_missing(self):
        # checkOneBranch returns False when there is no bzr branch in the
        # mirrored area for the database branch in old distroseries.
        self.checkOneBranch_old_branch_missing('mirrored')

    def checkOneBranch_new_stacked(self, branch_type):
        # checkOneBranch returns False when the bzr branch for the database
        # branch in new distroseries is stacked.
        assert branch_type in ('hosted', 'mirrored')
        db_branch = self.makeOfficialPackageBranch()
        b, _ = self.create_branch_and_tree(
            self.factory.getUniqueString(), hosted=(branch_type == 'hosted'))
        brancher = self.makeNewSeriesAndBrancher(db_branch.distroseries)
        new_db_branch = brancher.makeOneNewBranch(db_branch)
        if branch_type == 'hosted':
            url = new_db_branch.getPullURL()
        else:
            url = new_db_branch.warehouse_url
        Branch.open(url).set_stacked_on_url('/' + b.unique_name)
        ok = brancher.checkOneBranch(db_branch)
        self.assertFalse(ok)
        self.assertLogMessages([
            '^WARNING New branch at lp-%s:///.*/.*/.*/.* is stacked on '
            '/.*/.*/.*, should be unstacked.$' % branch_type,
            ])

    def test_checkOneBranch_new_hosted_stacked(self):
        # checkOneBranch returns False when the bzr branch in the hosted area
        # for the database branch in new distroseries is stacked.
        self.checkOneBranch_new_stacked('hosted')

    def test_checkOneBranch_new_mirrored_stacked(self):
        # checkOneBranch returns False when the bzr branch in the mirrored
        # area for the database branch in new distroseries is stacked.
        self.checkOneBranch_new_stacked('mirrored')

    def checkOneBranch_old_unstacked(self, branch_type):
        # checkOneBranch returns False when the bzr branch for the database
        # branch in old distroseries is not stacked.
        assert branch_type in ('hosted', 'mirrored')
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch.distroseries)
        brancher.makeOneNewBranch(db_branch)
        if branch_type == 'hosted':
            url = db_branch.getPullURL()
        else:
            url = db_branch.warehouse_url
        old_bzr_branch = Branch.open(url)
        old_bzr_branch.set_stacked_on_url(None)
        ok = brancher.checkOneBranch(db_branch)
        self.assertLogMessages([
            '^WARNING Old branch at lp-%s:///.*/.*/.*/.* is not stacked, '
            'should be stacked on /.*/.*/.*.$' % branch_type,
            '^.*has .* revisions.*$',
            ])
        self.assertFalse(ok)

    def test_checkOneBranch_old_hosted_unstacked(self):
        # checkOneBranch returns False when the bzr branch in the hosted area
        # for the database branch in old distroseries is not stacked.
        self.checkOneBranch_old_unstacked('hosted')

    def test_checkOneBranch_old_mirrored_unstacked(self):
        # checkOneBranch returns False when the bzr branch in the mirrored
        # area for the database branch in old distroseries is not stacked.
        self.checkOneBranch_old_unstacked('mirrored')

    def checkOneBranch_old_misstacked(self, branch_type):
        # checkOneBranch returns False when the bzr branch for the database
        # branch in old distroseries stacked on some other branch than the
        # branch in the new distroseries.
        assert branch_type in ('hosted', 'mirrored')
        db_branch = self.makeOfficialPackageBranch()
        b, _ = self.create_branch_and_tree(
            self.factory.getUniqueString(), hosted=(branch_type == 'hosted'))
        brancher = self.makeNewSeriesAndBrancher(db_branch.distroseries)
        brancher.makeOneNewBranch(db_branch)
        if branch_type == 'hosted':
            url = db_branch.getPullURL()
        else:
            url = db_branch.warehouse_url
        Branch.open(url).set_stacked_on_url('/' + b.unique_name)
        ok = brancher.checkOneBranch(db_branch)
        self.assertLogMessages([
            '^WARNING Old branch at lp-%s:///.*/.*/.*/.* is stacked on '
            '/.*/.*/.*, should be stacked on /.*/.*/.*.$' % branch_type,
            ])
        self.assertFalse(ok)

    def test_checkOneBranch_old_hosted_misstacked(self):
        # checkOneBranch returns False when the bzr branch in the hosted area
        # for the database branch in old distroseries stacked on some other
        # branch than the branch in the new distroseries.
        self.checkOneBranch_old_misstacked('hosted')

    def test_checkOneBranch_old_mirrored_misstacked(self):
        # checkOneBranch returns False when the bzr branch in the mirrored
        # area for the database branch in old distroseries stacked on some
        # other branch than the branch in the new distroseries.
        self.checkOneBranch_old_misstacked('mirrored')

    def checkOneBranch_old_has_revisions(self, branch_type):
        # checkOneBranch returns False when the bzr branch for the database
        # branch in old distroseries has a repository that contains revisions.
        assert branch_type in ('hosted', 'mirrored')
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch.distroseries)
        brancher.makeOneNewBranch(db_branch)
        if branch_type == 'hosted':
            url = db_branch.getPullURL()
        else:
            url = db_branch.warehouse_url
        old_bzr_branch = Branch.open(url)
        old_bzr_branch.create_checkout(
            self.factory.getUniqueString()).commit('')
        ok = brancher.checkOneBranch(db_branch)
        self.assertLogMessages([
            '^WARNING Repository at lp-%s:///.*/.*/.*/.* has 1 revisions.'
            % branch_type
            ])
        self.assertFalse(ok)

    def test_checkOneBranch_old_hosted_has_revisions(self):
        # checkOneBranch returns False when the bzr branch in the hosted area
        # for the database branch in old distroseries has a repository that
        # contains revisions.
        self.checkOneBranch_old_has_revisions('hosted')

    def test_checkOneBranch_old_mirrored_has_revisions(self):
        # checkOneBranch returns False when the bzr branch in the mirrored
        # area for the database branch in old distroseries has a repository
        # that contains revisions.
        self.checkOneBranch_old_has_revisions('mirrored')

    def checkOneBranch_old_has_null_tip(self, branch_type):
        # checkOneBranch returns False when the bzr branch for the database
        # branch in old distroseries has tip revision of 'null:'.
        assert branch_type in ('hosted', 'mirrored')
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch.distroseries)
        brancher.makeOneNewBranch(db_branch)
        if branch_type == 'hosted':
            url = db_branch.getPullURL()
        else:
            url = db_branch.warehouse_url
        old_bzr_branch = Branch.open(url)
        old_bzr_branch.set_last_revision_info(0, 'null:')
        ok = brancher.checkOneBranch(db_branch)
        self.assertLogMessages([
            '^WARNING Old branch at lp-%s:///.*/.*/.*/.* has null tip '
            'revision.' % branch_type
            ])
        self.assertFalse(ok)

    def test_checkOneBranch_old_hosted_has_null_tip(self):
        # checkOneBranch returns False when the bzr branch in the hosted area
        # for the database branch in old distroseries has tip revision of
        # 'null:'.
        self.checkOneBranch_old_has_null_tip('hosted')

    def test_checkOneBranch_old_mirrored_has_null_tip(self):
        # checkOneBranch returns False when the bzr branch in the mirrored
        # area for the database branch in old distroseries has tip revision of
        # 'null:'.
        self.checkOneBranch_old_has_null_tip('mirrored')

    def runBranchDistroScript(self, args):
        """Run the branch-distro.py script with the given arguments.

        ;param args: The arguments to pass to the branch-distro.py script.
        :return: A tuple (returncode, output).  stderr and stdout are both
            contained in the output.
        """
        script_path = os.path.join(config.root, 'scripts', 'branch-distro.py')
        process = Popen([script_path] + args, stdout=PIPE, stderr=STDOUT)
        output, error = process.communicate()
        return process.returncode, output

    def test_makeNewBranches_script(self):
        # Running the script with the arguments 'distro old-series new-series'
        # makes new branches in the new series.
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch.distroseries)
        returncode, output = self.runBranchDistroScript(
            ['-v', db_branch.distribution.name,
             brancher.old_distroseries.name, brancher.new_distroseries.name])
        self.assertEqual(0, returncode)
        self.assertEqual(
            'DEBUG   Processing ' + db_branch.unique_name + '\n', output)
        brancher.checkOneBranch(db_branch)

    def test_checkNewBranches_script_success(self):
        # Running the script with the arguments '--check distro old-series
        # new-series' checks that the branches in the new series are as
        # expected.
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch.distroseries)
        brancher.makeNewBranches()
        returncode, output = self.runBranchDistroScript(
            ['-v', '--check', db_branch.distribution.name,
             brancher.old_distroseries.name, brancher.new_distroseries.name])
        self.assertEqual(0, returncode)
        self.assertEqual(
            'DEBUG   Checking ' + db_branch.unique_name + '\n', output)
        brancher.checkOneBranch(db_branch)

    def test_checkNewBranches_script_failure(self):
        # Running the script with the arguments '--check distro old-series
        # new-series' checks that the branches in the new series are as
        # expected and logs warnings and exits with code 1 is things are not
        # as expected.
        db_branch = self.makeOfficialPackageBranch()
        brancher = self.makeNewSeriesAndBrancher(db_branch.distroseries)
        returncode, output = self.runBranchDistroScript(
            ['-v', '--check', db_branch.distribution.name,
             brancher.old_distroseries.name, brancher.new_distroseries.name])
        sp_path = brancher.new_distroseries.getSourcePackage(
            db_branch.sourcepackagename).path
        expected = '''\
        DEBUG   Checking %(branch_name)s
        WARNING No official branch found for %(sp_path)s
        ERROR   Check failed
        ''' % {'branch_name': db_branch.unique_name, 'sp_path': sp_path}
        self.assertEqual(
            textwrap.dedent(expected), output)
        self.assertEqual(1, returncode)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

