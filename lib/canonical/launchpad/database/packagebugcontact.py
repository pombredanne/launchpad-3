# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""Database API for the PackageBugContact table."""

__metaclass__ = type

from sqlobject import ForeignKey
from canonical.database.sqlbase import SQLBase

class PackageBugContact(SQLBase):
    """Database class for the package bug contact.

    This class is purely an implementation detail behind
    IDistributionSourcePackage.bugcontact. This class should otherwise never be
    imported and/or used directly.
    """
    distribution = ForeignKey(
        dbName="distribution", notNull=True, foreignKey="Distribution")
    sourcepackagename = ForeignKey(
        dbName="sourcepackagename", notNull=True, foreignKey="SourcePackageName")
    bugcontact = ForeignKey(
        dbName="bugcontact", notNull=True, foreignKey="Person")
