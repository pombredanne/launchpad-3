# Copyright 2006 Canonical Ltd.  All rights reserved.

import os

from canonical.config import config
from canonical.launchpad.scripts.supermirror.jobmanager import JobManager
from canonical.launchpad.scripts.supermirror.branchtargeter import branchtarget
from canonical.launchpad.scripts.supermirror.branchfactory import BranchFactory


def mirror(branches, managerClass=JobManager,
           lockfile=config.supermirror.masterlock):
    """Mirror the given branches into the directory specified in
    config.supermirror.branchesdest.
    
    branches must be a list of canonical.launchpad.database.branch.Branch
    objects.
    """
    mymanager = managerClass()
    branchesdest = config.supermirror.branchesdest
    branchfactory = BranchFactory()
    try:
        mymanager.lock(lockfilename=lockfile)
        mymanager.install()
        for branch in branches:
            path = branchtarget(branch.id)
            branchdest = os.path.join(branchesdest, path)
            branch = branchfactory.produce(branch.pull_url, branchdest)
            mymanager.add(branch)
        mymanager.run()
    finally:
        mymanager.uninstall()
        mymanager.unlock()

    return 0

