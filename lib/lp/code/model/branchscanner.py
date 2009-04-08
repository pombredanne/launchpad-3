# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Implementation of branch scanner utility."""

__metaclass__ = type
# Don't export anything. Instead get at this method using the utility.
__all__ = []


from storm.expr import Or

from zope.component import getUtility
from zope.interface import implements

from lp.code.model.branch import Branch
from lp.code.interfaces.branch import BranchType
from lp.code.interfaces.branchscanner import IBranchScanner
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)


class BranchScanner:

    implements(IBranchScanner)

    def getBranchesToScan(self):
        """See `IBranchScanner`"""
        # Return branches where the scanned and mirrored IDs don't match.
        # Branches with a NULL last_mirrored_id have never been
        # successfully mirrored so there is no point scanning them.
        # Branches with a NULL last_scanned_id have not been scanned yet,
        # so are included.
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(
            Branch,
            Branch.branch_type != BranchType.REMOTE,
            Branch.last_mirrored_id != None,
            Or(Branch.last_scanned_id == None,
               Branch.last_scanned_id != Branch.last_mirrored_id))
