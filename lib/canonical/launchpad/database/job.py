# Copyright 2008 Canonical Ltd.  All rights reserved.

"""ORM object representing jobs."""

__metaclass__ = type
__all__ = ['Job']


from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from zope.interface import implements

from canonical.launchpad.interfaces import IJob


class Job(SQLBase):

    implements(IJob)

    lease_expires = UtcDateTimeCol()
