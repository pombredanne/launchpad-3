# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Bzr back-end for importd."""

__metaclass__ = type

__all__ = ['BzrManager']


import os
import subprocess
import sys
import tempfile

from bzrlib.bzrdir import BzrDir

from canonical.config import config


class BzrManager:
    """Manage a bzr branch in importd.

    This class encapsulate all the bzr-specific code in importd.
    """

    def __init__(self, job):
        self.job = job
        self.logger = job.logger
        self.series_id = job.seriesID
        self.push_prefix = job.push_prefix

        # This is used only when running tests, to suppress the
        # scripts' output, but give it as an argument to sys.exit
        # if the script fails.
        self.silent = False

    def targetBranchName(self, dir):
        working_dir = self.job.getWorkingDir(dir)
        return self._targetTreePath(working_dir)

    def _targetTreePath(self, working_dir):
        return os.path.join(working_dir, "bzrworking")

    def createImportTarget(self, working_dir):
        """Create a bzrworking branch to perform an import into."""
        # XXX David Allouche 2006-07-28: fail if there is a mirror.
        path = self._targetTreePath(working_dir)
        BzrDir.create_standalone_workingtree(path)
        return path

    def mirrorBranch(self, working_dir):
        """Run scripts/importd-publish to publish bzrworking."""
        arguments = self._scriptCommand('importd-publish.py',
            [working_dir, str(self.series_id), self.push_prefix])
        self._runCommand(arguments)

    def getSyncTarget(self, working_dir):
        """Run scripts/importd-get-target to retrieve bzrworking.

        This is basically a `bzr branch`.  The `get` in the method
        name refers to the `baz get` command, which is nowadays
        called `bzr branch`.  So, `bzr branch $MIRROR $SYNC_TARGET`.
        """
        arguments = self._scriptCommand('importd-get-target.py',
            [working_dir, str(self.series_id), self.push_prefix])
        self._runCommand(arguments)
        return self._targetTreePath(working_dir)

    def _scriptCommand(self, name, arguments):
        return ([sys.executable, os.path.join(config.root, 'scripts', name)]
                + arguments)

    def _runCommand(self, arguments):
        stdin = open('/dev/null', 'r')
        retcode = subprocess.call(arguments, stdin=stdin)
        if retcode != 0:
            sys.exit(retcode)

