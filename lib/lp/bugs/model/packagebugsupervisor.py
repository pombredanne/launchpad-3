# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

"""Database API for the PackageBugSupervisor table."""

__metaclass__ = type

from sqlobject import ForeignKey

from canonical.database.sqlbase import SQLBase
from lp.registry.interfaces.person import validate_public_person

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
        storm_validator=validate_public_person)
