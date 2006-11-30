# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Launchpad Pillars share a namespace.

Pillars are currently Product, Project and Distribution.
"""

__metaclass__ = type

from zope.component import getUtility
from zope.interface import implements

from canonical.config import config
from canonical.database.sqlbase import cursor, sqlvalues
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.interfaces import (
        NotFoundError, IPillarSet, IDistributionSet, IProductSet, IProjectSet
        )

__all__ = ['PillarSet']


class PillarSet:
    implements(IPillarSet)

    def __contains__(self, name):
        """See IPillarSet."""
        cur = cursor()
        cur.execute("SELECT TRUE FROM PillarName WHERE name=%(name)s", vars())
        if cur.fetchone() is None:
            return False
        else:
            return True

    def __getitem__(self, name):
        """See IPillarSet."""
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

    def search(self, text, limit=config.launchpad.default_batch_size):
        """See IPillarSet."""
        base_query = """
            SELECT 'distribution' AS otype, id, name, title, description,
                   rank(fti, ftq(%(text)s)) AS rank
            FROM distribution
            WHERE fti @@ ftq(%(text)s)
                AND name != lower(%(text)s)
                AND lower(title) != lower(%(text)s)

            UNION ALL

            SELECT 'product' AS otype, id, name, title, description,
                rank(fti, ftq(%(text)s)) AS rank
            FROM product
            WHERE fti @@ ftq(%(text)s)
                AND name != lower(%(text)s)
                AND lower(title) != lower(%(text)s)

            UNION ALL

            SELECT 'project' AS otype, id, name, title, description,
                rank(fti, ftq(%(text)s)) AS rank
            FROM project
            WHERE fti @@ ftq(%(text)s)
                AND name != lower(%(text)s)
                AND lower(title) != lower(%(text)s)

            UNION ALL

            SELECT 'distribution' AS otype, id, name, title, description,
                9999999 AS rank
            FROM distribution 
            WHERE name = lower(%(text)s) OR lower(title) = lower(%(text)s)

            UNION ALL

            SELECT 'project' AS otype, id, name, title, description,
                9999999 AS rank
            FROM project
            WHERE name = lower(%(text)s) OR lower(title) = lower(%(text)s)

            UNION ALL

            SELECT 'product' AS otype, id, name, title, description,
                9999999 AS rank
            FROM product
            WHERE name = lower(%(text)s) OR lower(title) = lower(%(text)s)

            ORDER BY rank DESC
            """ % sqlvalues(text=text)
        count_query = "SELECT COUNT(*) FROM (%s) AS TMP_COUNT" % base_query
        query = "%s LIMIT %d" % (base_query, limit + 1)
        cur = cursor()
        cur.execute(query)
        keys = ['type', 'id', 'name', 'title', 'description', 'rank']
        # People shouldn't be calling this method with too big limits
        longest_expected = 2 * config.launchpad.default_batch_size
        return shortlist(
            [dict(zip(keys, values)) for values in cur.fetchall()],
            longest_expected=longest_expected)

