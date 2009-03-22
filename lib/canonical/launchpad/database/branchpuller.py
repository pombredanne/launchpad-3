# Copyright 2009 Canonical Ltd.  All rights reserved.

"""The way the branch puller talks to the database."""

__metaclass__ = type
# Export nothing. This code should be obtained via utilities.
__all__ = []

from datetime import timedelta

from sqlobject.sqlbuilder import AND

from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.launchpad.database.branch import Branch
from canonical.launchpad.interfaces.branchpuller import IBranchPuller


class BranchPuller:

    implements(IBranchPuller)

    MAXIMUM_MIRROR_FAILURES = 5
    MIRROR_TIME_INCREMENT = timedelta(hours=6)

    def getPullQueue(self, branch_type):
        """See `IBranchSet`."""
        return Branch.select(
            AND(Branch.q.branch_type == branch_type,
                Branch.q.next_mirror_time <= UTC_NOW),
            prejoins=['owner', 'product'], orderBy='next_mirror_time')
