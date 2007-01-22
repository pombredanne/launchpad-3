# Copyright 2006 Canonical Ltd.  All rights reserved.

import urllib

from canonical.config import config
from canonical.launchpad.scripts.supermirror.jobmanager import (
    JobManager, LockError)
from canonical.authserver.client.branchstatus import BranchStatusClient


def mirror(logger, managerClass=JobManager):
    """Mirror all current branches that need to be mirrored."""
    mymanager = managerClass()
    client = BranchStatusClient()

    try:
        mymanager.lock()
    except LockError:
        return 0

    try:
        mymanager.addBranches(client)
        mymanager.run(logger)
    finally:
        mymanager.unlock()
    return 0

