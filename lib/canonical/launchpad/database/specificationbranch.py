# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""Database classes for linking specifications and branches."""

__metaclass__ = type

__all__ = ["SpecificationBranch"]

from sqlobject import ForeignKey, StringCol

from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import ISpecificationBranch


class SpecificationBranch(SQLBase):
    """See canonical.launchpad.interfaces.ISpecificationBranch."""
    implements(ISpecificationBranch)

    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    specification = ForeignKey(dbName="specification",
                               foreignKey="Specification", notNull=True)
    branch = ForeignKey(dbName="branch", foreignKey="Branch", notNull=True)
    summary = StringCol(dbName="summary", notNull=False, default=None)
