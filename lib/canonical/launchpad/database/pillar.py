# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Launchpad Pillars share a namespace.

Pillars are currently Product, Project and Distribution.
"""

__metaclass__ = type

from zope.component import getUtility
from zope.interface import implements

from sqlobject import ForeignKey, StringCol, BoolCol

from canonical.database.sqlbase import cursor, SQLBase
from canonical.launchpad.interfaces import (
        NotFoundError, IPillarNameSet, IPillarName,
        IDistributionSet, IProductSet, IProjectSet,
        )

__all__ = ['PillarNameSet', 'PillarName']


class PillarNameSet:
    implements(IPillarNameSet)

    def __contains__(self, name):
        """See IPillarNameSet."""
        cur = cursor()
        cur.execute("SELECT TRUE FROM PillarName WHERE name=%(name)s", vars())
        if cur.fetchone() is None:
            return False
        else:
            return True

    def __getitem__(self, name):
        """See IPillarNameSet."""
        # We could attempt to do this in a single database query, but I
        # expect that doing two queries will be faster that OUTER JOINing
        # the Project, Product and Distribution tables (and this approach
        # works better with SQLObject too.

        # Retrieve information out of the PillarName table.
        cur = cursor()
        cur.execute("""
            SELECT id, product, project, distribution
            FROM PillarName
            WHERE name=%(name)s
            """, vars())
        row = cur.fetchone()
        if row is None:
            raise NotFoundError(name)

        assert len([column for column in row[1:] if column is None]) == 2, """
                One (and only one) of project, project or distribution may
                be NOT NULL
                """

        id, product, project, distribution = row

        if product is not None:
            return getUtility(IProductSet).get(product)
        elif project is not None:
            return getUtility(IProjectSet).get(project)
        else:
            return getUtility(IDistributionSet).get(distribution)


class PillarName(SQLBase):
    implements(IPillarName)

    _table = 'PillarName'

    name = StringCol(dbName='name', notNull=True, unique=True, alternateID=True)
    product = ForeignKey(foreignKey='Product', dbName='product')
    project = ForeignKey(foreignKey='Project', dbName='project')
    distribution = ForeignKey(foreignKey='Distribution', dbName='distribution')
    active = BoolCol(dbName='active', notNull=True, default=True)


