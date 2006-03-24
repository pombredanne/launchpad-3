# Copyright 2006 Canonical Ltd.  All rights reserved.

import urllib

from canonical.config import config
from canonical.launchpad.scripts.supermirror.jobmanager import (
    JobManager, LockError)


def mirror(managerClass=JobManager, urllibOpener=urllib.urlopen):
    """Mirror all current branches that need to be mirrored."""
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

