# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['ProjectBounty',]

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.launchpad.interfaces import IProjectBounty

from canonical.database.sqlbase import SQLBase


class ProjectBounty(SQLBase):
    """A relationship between a project and a bounty."""

    implements(IProjectBounty)

    _table='ProjectBounty'
    bounty = ForeignKey(dbName='bounty', foreignKey='Bounty', notNull=True)
    project = ForeignKey(dbName='project', foreignKey='Project',
        notNull=True)

