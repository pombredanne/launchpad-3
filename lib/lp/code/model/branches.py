# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Implementation of public webservice interface for branches."""

__metaclass__ = type
__all__ = []


from storm.expr import Desc

from zope.component import getUtility
from zope.interface import implements

from lp.code.model.branch import Branch
from lp.code.interfaces.branches import IBranches
from lp.code.interfaces.branchcollection import IAllBranches
from lp.code.interfaces.branchlookup import IBranchLookup


class Branches:
    """See `IBranches`."""

    implements(IBranches)

    def getByUniqueName(self, unique_name):
        """See `IBranches`."""
        return getUtility(IBranchLookup).getByUniqueName(unique_name)

    def getByUrl(self, url):
        """See `IBranches`."""
        return getUtility(IBranchLookup).getByUrl(url)

    def getBranches(user, limit=50):
        """See `IBranches`."""
        user_branches = getUtility(IAllBranches).visibleByUser(user)
        branches = user_branches.scanned().getBranches()
        branches.order_by(
            Desc(Branch.date_last_modified), Desc(Branch.id))
        branches.config(limit=limit)
        return branches
