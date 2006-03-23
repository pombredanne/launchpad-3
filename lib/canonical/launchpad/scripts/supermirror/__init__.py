# Copyright 2006 Canonical Ltd.  All rights reserved.

import urllib

from canonical.config import config
from canonical.launchpad.scripts.supermirror.jobmanager import (
    JobManager, LockError)


def mirror(managerClass=JobManager, urllibOpener=urllib.urlopen):
    """Mirror the given branches into the directory specified in
    config.supermirror.branchesdest.
    
    branches must be a list of canonical.launchpad.database.branch.Branch
    objects.
    """
    mymanager = managerClass()
    try:
        mymanager.lock()
    except LockError:
        return 0

    try:
        branchdata = urllibOpener(config.supermirror.branchlistsource)
        for branch in mymanager.branchStreamToBranchList(branchdata):
            mymanager.add(branch)
        mymanager.run()
    finally:
        mymanager.unlock()
    return 0

