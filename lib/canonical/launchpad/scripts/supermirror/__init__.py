# Copyright 2006 Canonical Ltd.  All rights reserved.

import datetime
import urllib

import pytz

from canonical.config import config
from canonical.launchpad.scripts.supermirror.jobmanager import (
    JobManager, LockError)
from canonical.authserver.client.branchstatus import BranchStatusClient


UTC = pytz.timezone('UTC')


def mirror(logger, managerClass):
    """Mirror all current branches that need to be mirrored."""
    mymanager = managerClass()
    client = BranchStatusClient()

    try:
        mymanager.lock()
    except LockError, exception:
        logger.info('Could not acquire lock: %s', exception)
        return 0

    try:
        date_started = datetime.datetime.now(UTC)
        mymanager.addBranches(client)
        mymanager.run(logger)
        date_completed = datetime.datetime.now(UTC)
        mymanager.recordActivity(client, date_started, date_completed)
    finally:
        mymanager.unlock()
    return 0

