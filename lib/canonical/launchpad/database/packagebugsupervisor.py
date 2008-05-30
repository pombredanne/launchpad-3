# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""Database API for the PackageBugSupervisor table."""

__metaclass__ = type

from sqlobject import ForeignKey
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.validators.person import public_person_validator


# This class is not currently in use. It is reserved for future
# implementation of package bug supervisors.

class PackageBugSupervisor(SQLBase):
    """Database class for the package bug supervisor.

    This class is purely an implementation detail behind
    `IDistributionSourcePackage.bug_supervisor`. This class should otherwise
    never be imported and/or used directly.
    """
    distribution = ForeignKey(
        dbName="distribution", notNull=True, foreignKey="Distribution")
    sourcepackagename = ForeignKey(
        dbName="sourcepackagename", notNull=True,
        foreignKey="SourcePackageName")
    bug_supervisor = ForeignKey(
        dbName="bug_supervisor", notNull=True, foreignKey="Person",
        validator=public_person_validator)
