# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Implementation of branch scanner utility."""

__metaclass__ = type
# Don't export anything. Instead get at this method using the utility.
__all__ = []

from zope.interface import implements

from canonical.database.sqlbase import quote
from canonical.launchpad.database.branch import Branch
from canonical.launchpad.interfaces.branch import BranchType
from canonical.launchpad.interfaces.branchscanner import IBranchScanner


class BranchScanner:

    implements(IBranchScanner)

    def getBranchesToScan(self):
        """See `IBranchSet`"""
        # Return branches where the scanned and mirrored IDs don't match.
        # Branches with a NULL last_mirrored_id have never been
        # successfully mirrored so there is no point scanning them.
        # Branches with a NULL last_scanned_id have not been scanned yet,
        # so are included.

        return Branch.select('''
            Branch.branch_type <> %s AND
            Branch.last_mirrored_id IS NOT NULL AND
            (Branch.last_scanned_id IS NULL OR
             Branch.last_scanned_id <> Branch.last_mirrored_id)
            ''' % quote(BranchType.REMOTE))
