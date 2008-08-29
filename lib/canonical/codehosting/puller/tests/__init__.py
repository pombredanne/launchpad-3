# Copyright 2006-2008 Canonical Ltd.  All rights reserved.

"""Common code for the puller tests."""

__metaclass__ = type

import os
import shutil
from StringIO import StringIO

from bzrlib.tests import TestCaseWithTransport
from bzrlib.urlutils import local_path_from_url

from canonical.codehosting import branch_id_to_path
from canonical.codehosting.puller.worker import (
    BranchOpener, PullerWorker, PullerWorkerProtocol)
from canonical.codehosting.tests.helpers import LoomTestMixin
from canonical.config import config
from canonical.launchpad.testing import TestCaseWithFactory


class AcceptAnythingOpener(BranchOpener):
    """A specialization of `BranchOpener` that opens any branch."""

    def checkOneURL(self, url):
        """See `BranchOpener.checkOneURL`.

        Accept anything, to make testing easier.
        """
        pass


class PullerWorkerMixin:
    """Mixin for tests that want to make PullerWorker objects.

    Assumes that it is mixed into a class that runs in a temporary directory,
    such as `TestCaseInTempDir` and that `get_transport` is provided as a
    method.
    """

    def makePullerWorker(self, src_dir=None, dest_dir=None, branch_type=None,
                         protocol=None, oops_prefix=None):
        """Anonymous creation method for PullerWorker."""
        if protocol is None:
            protocol = PullerWorkerProtocol(StringIO())
        if oops_prefix is None:
            oops_prefix = ''
        if branch_type is None:
            opener = AcceptAnythingOpener()
        else:
            opener = None
        return PullerWorker(
            src_dir, dest_dir, branch_id=1, unique_name='foo/bar/baz',
            branch_type=branch_type, protocol=protocol, branch_opener=opener,
            oops_prefix=oops_prefix)


class PullerBranchTestCase(TestCaseWithTransport, TestCaseWithFactory,
                           LoomTestMixin):
    """Some useful code for the more-integration-y puller tests."""

    def setUp(self):
        TestCaseWithTransport.setUp(self)
        TestCaseWithFactory.setUp(self)

    def getHostedPath(self, branch):
        """Return the path of 'branch' in the upload area."""
        return os.path.join(
            config.codehosting.branches_root, branch_id_to_path(branch.id))

    def getMirroredPath(self, branch):
        """Return the path of 'branch' in the supermirror area."""
        return os.path.join(
            config.supermirror.branchesdest, branch_id_to_path(branch.id))

    def makeCleanDirectory(self, path):
        """Guarantee an empty branch upload area."""
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path)

    def pushToBranch(self, branch, tree=None):
        """Push a Bazaar branch to a given Launchpad branch's hosted area.

        Use this to test mirroring a hosted branch.

        :param branch: A Launchpad Branch object.
        """
        hosted_path = self.getHostedPath(branch)
        if tree is None:
            tree = self.make_branch_and_tree('branch-path')
            tree.commit('rev1')
        out, err = self.run_bzr(
            ['push', '--create-prefix', '-d',
             local_path_from_url(tree.branch.base), hosted_path],
            retcode=None)
        # We want to be sure that a new branch was indeed created.
        self.assertEqual("Created new branch.\n", err)
