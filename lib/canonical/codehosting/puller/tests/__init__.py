# Copyright 2006-2008 Canonical Ltd.  All rights reserved.

"""Common code for the puller tests."""

__metaclass__ = type

import os
import shutil
from StringIO import StringIO

from bzrlib.urlutils import local_path_from_url

from canonical.codehosting import branch_id_to_path
from canonical.codehosting.puller.worker import (
    BranchOpener, PullerWorker, PullerWorkerProtocol)
from canonical.codehosting.tests.helpers import BranchTestCase
from canonical.config import config


class AcceptAnythingOpener(BranchOpener):
    def checkOneURL(self, url):
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
        if src_dir is None:
            src_dir = self.get_transport('source-branch').base
        if dest_dir is None:
            dest_dir = './dest-branch'
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


class PullerBranchTestCase(BranchTestCase):
    """Some useful code for the more-integration-y puller tests."""

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
        """Push a Bazaar branch to a given Launchpad branch.

        :param branch: A Launchpad Branch object.
        """
        hosted_path = self.getHostedPath(branch)
        if tree is None:
            tree = self.createTemporaryBazaarBranchAndTree()
        out, err = self.run_bzr(
            ['push', '--create-prefix', '-d',
             local_path_from_url(tree.branch.base), hosted_path],
            retcode=None)
        # We want to be sure that a new branch was indeed created.
        self.assertEqual("Created new branch.\n", err)
