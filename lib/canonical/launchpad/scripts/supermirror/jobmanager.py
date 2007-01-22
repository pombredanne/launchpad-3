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

    def run(self, logger):
        """Run all branches_to_mirror registered with the JobManager"""
        while self.branches_to_mirror:
            self.branches_to_mirror.pop(0).mirror(logger)

    def addBranches(self, branch_status_client):
        """Queue branches from the list provided by the branch status client

        The BranchStatusClient.getBranchPullQueue() method returns a
        list of (branch_id, url) pairs.  Each pair is converted to a
        BranchToMirror object and added to the branches_to_mirror
        list.
        """
        branches_to_pull = branch_status_client.getBranchPullQueue()
        destination = config.supermirror.branchesdest
        for branch_id, branch_src in branches_to_pull:
            branch_src = branch_src.strip()
            path = branchtarget(branch_id)
            branch_dest = os.path.join(destination, path)
            branch = BranchToMirror(
                branch_src, branch_dest, branch_status_client, branch_id)
            self.add(branch)

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

