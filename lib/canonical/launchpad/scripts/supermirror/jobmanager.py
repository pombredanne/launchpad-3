# Copyright 2006 Canonical Ltd.  All rights reserved.

import os
import socket

from contrib.glock import GlobalLock, LockAlreadyAcquired

from canonical.config import config
from canonical.launchpad.scripts.supermirror.branchtargeter import branchtarget
from canonical.launchpad.scripts.supermirror.branchtomirror import (
    BranchToMirror)


class JobManager:
    """Schedule and manage the mirroring of branches.

    The jobmanager is responsible for organizing the mirroring of all
    branches.
    """

    def __init__(self, branch_status_client, branch_type):
        self.branch_status_client = branch_status_client
        self.branches_to_mirror = []
        self.actualLock = None
        self.branch_type = branch_type
        self.name = 'branch-puller-%s' % branch_type.name.lower()
        self.lockfilename = '/var/lock/launchpad-%s.lock' % self.name
        self._addBranches(
            branch_status_client.getBranchPullQueue(branch_type.name))

    def run(self, logger):
        """Run all branches_to_mirror registered with the JobManager"""
        logger.info('%d branches to mirror', len(self.branches_to_mirror))
        while self.branches_to_mirror:
            self.branches_to_mirror.pop(0).mirror(logger)
        logger.info('Mirroring complete')

    def _addBranches(self, branches_to_pull):
        for branch_id, branch_src, unique_name in branches_to_pull:
            self.branches_to_mirror.append(
                self.getBranchToMirror(
                    self.branch_status_client, branch_id, branch_src,
                    unique_name))

    def getBranchToMirror(self, branch_status_client, branch_id, branch_src,
                          unique_name):
        branch_src = branch_src.strip()
        path = branchtarget(branch_id)
        branch_dest = os.path.join(config.supermirror.branchesdest, path)
        return BranchToMirror(
            branch_src, branch_dest, branch_status_client, branch_id,
            unique_name, self.branch_type)

    def lock(self):
        self.actualLock = GlobalLock(self.lockfilename)
        try:
            self.actualLock.acquire()
        except LockAlreadyAcquired:
            raise LockError(self.lockfilename)

    def unlock(self):
        self.actualLock.release()

    def recordActivity(self, branch_status_client,
                       date_started, date_completed):
        """Record successful completion of the script."""
        branch_status_client.recordSuccess(
            self.name, socket.gethostname(), date_started, date_completed)


class LockError(StandardError):

    def __init__(self, lockfilename):
        self.lockfilename = lockfilename

    def __str__(self):
        return 'Jobmanager unable to get master lock: %s' % self.lockfilename

