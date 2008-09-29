# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""Database classes for linking specifications and branches."""

__metaclass__ = type

__all__ = [
    "SpecificationBranch",
    "SpecificationBranchSet",
    ]

from sqlobject import ForeignKey, IN, StringCol

from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import (
    ISpecificationBranch, ISpecificationBranchSet)
from canonical.launchpad.validators.person import validate_public_person


class SpecificationBranch(SQLBase):
    """See `ISpecificationBranch`."""
    implements(ISpecificationBranch)

    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    specification = ForeignKey(dbName="specification",
                               foreignKey="Specification", notNull=True)
    branch = ForeignKey(dbName="branch", foreignKey="Branch", notNull=True)
    summary = StringCol(dbName="summary", notNull=False, default=None)

    registrant = ForeignKey(
        dbName='registrant', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)


class SpecificationBranchSet:
    """See `ISpecificationBranchSet`."""
    implements(ISpecificationBranchSet)

    def getSpecificationBranchesForBranches(self, branches, user):
        """See `ISpecificationBranchSet`."""
        branch_ids = [branch.id for branch in branches]
        if not branch_ids:
            return []

        # When specification gain the ability to be private, this
        # method will need to be updated to enforce the privacy checks.
        return SpecificationBranch.select(
            IN(SpecificationBranch.q.branchID, branch_ids))
