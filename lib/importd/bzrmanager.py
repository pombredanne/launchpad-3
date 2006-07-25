# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Bzr back-end for importd."""

__metaclass__ = type

__all__ = ['BzrManager']


import os
import subprocess
import sys

from bzrlib.bzrdir import BzrDir

from canonical.config import config


class BzrManager:
    """Manage a bzr branch in importd.

    This class encapsulate all the bzr-specific code in importd.
    """

    def __init__(self, job):
        self.logger = job.logger
        self.series_id = job.seriesID
        self.push_prefix = job.push_prefix
        self.silent = False

    def createMaster(self):
       """Do nothing. For compatibility with ArchiveManager."""

    def createMirror(self):
       """Do nothing. For compatibility with ArchiveManager."""

    def nukeMaster(self):
       """Do nothing. For compatibility with ArchiveManager."""

    def rollbackToMirror(self):
        """Do nothing. For compatibility with ArchiveManager."""

    def _targetTreePath(self, working_dir):
        return os.path.join(working_dir, "bzrworking")

    def createImportTarget(self, working_dir):
        path = self._targetTreePath(working_dir)
        BzrDir.create_standalone_workingtree(path)
        # fail if there is a mirror

    # def getSyncTarget(self, working_dir):
    # fail if there is no mirror

    def mirrorBranch(self, directory):
        # produce line-by-line progress
        # fail if there is divergence
        stdout = None
        stderr = None
        stdin = open('/dev/null', 'r')
        if self.silent:
            stdout = stderr = open('/dev/null', 'w')
        retcode = subprocess.call([
            sys.executable,
            os.path.join(config.root, 'scripts', 'importd-publish.py'),
            directory, str(self.series_id), self.push_prefix],
            stdin=stdin, stdout=stdout, stderr=stderr)
        if retcode != 0:
            # failure in the subprocess should bubble up to CommandLineRunner
            # for buildbot to get the non-zero exit status. We could use any
            # exception here, but SystemExit seems appropriate.
            sys.exit(retcode)
