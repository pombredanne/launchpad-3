# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The way the branch puller talks to the database."""

__metaclass__ = type
# Export nothing. This code should be obtained via utilities.
__all__ = []

from datetime import timedelta

from zope.component import getUtility
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from lp.code.enums import BranchType
from lp.code.interfaces.branchpuller import IBranchPuller
from lp.code.model.branch import Branch


class BranchPuller:
    """See `IBranchPuller`."""

    implements(IBranchPuller)

    MAXIMUM_MIRROR_FAILURES = 5
    MIRROR_TIME_INCREMENT = timedelta(hours=6)

    def acquireBranchToPull(self, *branch_types):
        """See `IBranchPuller`."""
        if not branch_types:
            branch_types = (BranchType.MIRRORED, BranchType.IMPORTED)
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        branch = store.find(
            Branch,
            Branch.next_mirror_time <= UTC_NOW,
            Branch.branch_type.is_in(branch_types)).order_by(
                Branch.next_mirror_time).first()
        if branch is not None:
            branch.startMirroring()
        return branch
