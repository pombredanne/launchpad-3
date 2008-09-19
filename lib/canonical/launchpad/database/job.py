# Copyright 2008 Canonical Ltd.  All rights reserved.

"""ORM object representing jobs."""

__metaclass__ = type
__all__ = ['Job', 'JobDependency']


from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from sqlobject import IntCol
from storm.references import ReferenceSet
from zope.interface import implements

from canonical.launchpad.interfaces import IJob


class Job(SQLBase):

    implements(IJob)

    lease_expires = UtcDateTimeCol()

    def destroySelf(self):
        self.dependants.clear()
        self.prerequisites.clear()
        SQLBase.destroySelf(self)


class JobDependency(SQLBase):

    __storm_primary__ = "prerequisite", "dependant"
    prerequisite = IntCol()
    dependant = IntCol()

Job.prerequisites = ReferenceSet(
    Job.id, JobDependency.dependant, JobDependency.prerequisite, Job.id)

Job.dependants = ReferenceSet(
    Job.id, JobDependency.prerequisite, JobDependency.dependant, Job.id)
