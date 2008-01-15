# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Helper methods for branch tests and pagetest."""

__metaclass__ = type
__all__ = [
    'make_branch_dormant',
    'reset_all_branch_last_modified',
    ]

from datetime import datetime, timedelta
import pytz

from canonical.config import config
from canonical.launchpad.ftests import login, logout
from canonical.launchpad.database.branch import BranchSet

def reset_all_branch_last_modified(last_modified=datetime.now(pytz.UTC)):
    """Reset the date_last_modifed value on all the branches.

    DO NOT use this in a non-pagetest.
    """
    login('foo.bar@canonical.com')
    branch_set = BranchSet()
    for branch in branch_set:
        branch.date_last_modified = last_modified
        branch.syncUpdate()
    logout()


def make_branch_dormant(unique_name):
    """Updates the branch's date_last_modified to make the branch dormant.

    DO NOT use this in a non-pagetest.
    """
    login('foo.bar@canonical.com')
    branch = BranchSet().getByUniqueName(unique_name)
    days = config.launchpad.branch_dormant_days + 1
    branch.date_last_modified = datetime.now(pytz.UTC) - timedelta(days=days)
    branch.syncUpdate()
    logout()
