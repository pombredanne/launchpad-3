# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""XXX write me."""

__metaclass__ = type

import unittest

from bzrlib.bzrdir import BzrDir
from bzrlib.errors import NotStacked
from bzrlib.tests import TestCaseWithTransport
from bzrlib.transport.chroot import ChrootServer

from lp.codehosting.branch_ubuntu import switch_branches
from lp.codehosting.vfs import branch_id_to_path


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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

