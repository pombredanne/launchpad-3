# Copyright 2006 Canonical Ltd.  All rights reserved.

import os

from canonical.config import config
from canonical.launchpad.scripts import lockfile
from canonical.launchpad.scripts.supermirror.branchtargeter import branchtarget
from canonical.launchpad.scripts.supermirror.branchtomirror import (
    BranchToMirror)


class JobManager:
    """Schedule and manage the mirroring of branches.
    
    The jobmanager is responsible for organizing the mirroring of all
    branches.
    """

    def __init__(self):
        self.branches_to_mirror = []
        self.actualLock = None
    
    def add (self, branch_to_mirror):
        """Add a branch to mirror to the JobManager."""
        self.branches_to_mirror.append(branch_to_mirror)

    def run(self):
        """Run all branches_to_mirror registered with the JobManager"""
        while self.branches_to_mirror:
            self.branches_to_mirror.pop().mirror()

    def branchStreamToBranchList(self, inputstream):
        """Convert a stream of branch URLS to list of branch objects.
        
        This function takes a file handle associated with a text file of
        the form:
            
            LAUNCHPAD_ID URL_FOR_BRANCH
            ...
            LAUNCHPAD_ID URL_FOR_BRANCH

        This series of urls is converted into a python list of branch
        objects of the appropriate type.
        """
        branches = []
        destination = config.supermirror.branchesdest
        for line in inputstream.readlines():
            branchnum, branchsrc = line.split(" ")
            branchsrc = branchsrc.strip()
            path = branchtarget(branchnum)
            branchdest = os.path.join(destination, path)
            branches.append(BranchToMirror(branchsrc, branchdest))
        return branches

    def lock(self, lockfilename=config.supermirror.masterlock):
        self.actualLock = lockfile.LockFile(lockfilename)
        try:
            self.actualLock.acquire()
        except OSError, e:
            raise LockError(lockfilename)

    def unlock(self):
        self.actualLock.release()


class LockError(StandardError):

    def __init__(self, lockfilename):
        self.lockfilename = lockfilename

    def __str__(self):
        return 'Jobmanager unable to get master lock: %s' % self.lockfilename

