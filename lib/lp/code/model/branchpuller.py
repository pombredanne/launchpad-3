# Copyright 2009 Canonical Ltd.  All rights reserved.

"""The way the branch puller talks to the database."""

__metaclass__ = type
# Export nothing. This code should be obtained via utilities.
__all__ = []

from datetime import timedelta

from storm.expr import LeftJoin, Join
from zope.component import getUtility
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from lp.code.model.branch import Branch
from lp.registry.model.person import Owner
from lp.registry.model.product import Product
from lp.code.interfaces.branch import BranchType, BranchTypeError
from lp.code.interfaces.branchpuller import IBranchPuller
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)


class BranchPuller:
    """See `IBranchPuller`."""

    implements(IBranchPuller)

    MAXIMUM_MIRROR_FAILURES = 5
    MIRROR_TIME_INCREMENT = timedelta(hours=6)

    def getPullQueue(self, branch_type):
        """See `IBranchPuller`."""
        if branch_type == BranchType.REMOTE:
            raise BranchTypeError("No pull queue for REMOTE branches.")
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        # Prejoin on owner and product to preserve existing behaviour.
        # XXX: JonathanLange 2009-03-22 spec=package-branches: This prejoin is
        # inappropriate in the face of package branches.
        prejoin = store.using(
            Branch,
            LeftJoin(Product, Branch.product == Product.id),
            Join(Owner, Branch.owner == Owner.id))
        return prejoin.find(
            Branch,
            Branch.branch_type == branch_type,
            Branch.next_mirror_time <= UTC_NOW).order_by(
                Branch.next_mirror_time)

    def acquireBranchToPull(self):
        """See `IBranchPuller`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        branch = store.find(
            Branch,
            Branch.next_mirror_time <= UTC_NOW).order_by(
                Branch.next_mirror_time).one()
        if branch is not None:
            branch.startMirroring()
        return branch
