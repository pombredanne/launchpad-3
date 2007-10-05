# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Launchpad Pillars share a namespace.

Pillars are currently Product, Project and Distribution.
"""

__metaclass__ = type

from zope.component import getUtility
from zope.interface import implements

from sqlobject import ForeignKey, StringCol, BoolCol

from canonical.config import config
from canonical.database.sqlbase import cursor, SQLBase, sqlvalues
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.interfaces import (
        NotFoundError, IPillarNameSet, IPillarName,
        IProduct, IDistribution,
        IDistributionSet, IProductSet, IProjectSet,
        )

__all__ = [
    'pillar_sort_key',
    'PillarNameSet',
    'PillarName',
    ]


def pillar_sort_key(pillar):
    """A sort key for a set of pillars. We want:

          - products first, alphabetically
          - distributions, with ubuntu first and the rest alphabetically
    """
    product_name = None
    distribution_name = None
    if IProduct.providedBy(pillar):
        product_name = pillar.name
    elif IDistribution.providedBy(pillar):
        distribution_name = pillar.name
    # Move ubuntu to the top.
    if distribution_name == 'ubuntu':
        distribution_name = '-'

    return (distribution_name, product_name)


class PillarNameSet:
    implements(IPillarNameSet)

    def __contains__(self, name):
        """See IPillarNameSet."""
        cur = cursor()
        cur.execute("""
            SELECT TRUE
            FROM PillarName
            WHERE name=%(name)s AND active IS TRUE
            """, {'name': name})
        if cur.fetchone() is None:
            return False
        else:
            return True

    def __getitem__(self, name):
        """See IPillarNameSet."""
        pillar = self.getByName(name, ignore_inactive=True)
        if pillar is None:
            raise NotFoundError(name)
        return pillar

    def getByName(self, name, ignore_inactive=False):
        """Return the pillar with the given name.

        If ignore_inactive is True, then only active pillars are considered.

        If no pillar is found, None is returned.
        """
        # We could attempt to do this in a single database query, but I
        # expect that doing two queries will be faster that OUTER JOINing
        # the Project, Product and Distribution tables (and this approach
        # works better with SQLObject too.

        # Retrieve information out of the PillarName table.
        cur = cursor()
        query = """
            SELECT id, product, project, distribution
            FROM PillarName
            WHERE name=%(name)s
            """
        if ignore_inactive:
            query += " AND active IS TRUE"
        cur.execute(query, {'name': name})
        row = cur.fetchone()
        if row is None:
            return None

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

    def build_search_query(self, text):
        return """
            SELECT 'distribution' AS otype, id, name, title, description,
                   icon,
                   rank(fti, ftq(%(text)s)) AS rank
            FROM distribution
            WHERE fti @@ ftq(%(text)s)
                AND name != lower(%(text)s)
                AND lower(title) != lower(%(text)s)

            UNION ALL

            SELECT 'project' AS otype, id, name, title, description, icon,
                rank(fti, ftq(%(text)s)) AS rank
            FROM product
            WHERE fti @@ ftq(%(text)s)
                AND name != lower(%(text)s)
                AND lower(title) != lower(%(text)s)
                AND active IS TRUE

            UNION ALL

            SELECT 'project group' AS otype, id, name, title, description,
                icon,
                rank(fti, ftq(%(text)s)) AS rank
            FROM project
            WHERE fti @@ ftq(%(text)s)
                AND name != lower(%(text)s)
                AND lower(title) != lower(%(text)s)
                AND active IS TRUE

            UNION ALL

            SELECT 'distribution' AS otype, id, name, title, description,
                icon,
                9999999 AS rank
            FROM distribution
            WHERE name = lower(%(text)s) OR lower(title) = lower(%(text)s)

            UNION ALL

            SELECT 'project group' AS otype, id, name, title, description,
                icon,
                9999999 AS rank
            FROM project
            WHERE (name = lower(%(text)s) OR lower(title) = lower(%(text)s))
                AND active IS TRUE

            UNION ALL

            SELECT 'project' AS otype, id, name, title, description,
                icon,
                9999999 AS rank
            FROM product
            WHERE (name = lower(%(text)s) OR lower(title) = lower(%(text)s))
                AND active IS TRUE

            """ % sqlvalues(text=text)

    def count_search_matches(self, text):
        base_query = self.build_search_query(text)
        count_query = "SELECT COUNT(*) FROM (%s) AS TMP_COUNT" % base_query
        cur = cursor()
        cur.execute(count_query)
        return cur.fetchone()[0]

    def search(self, text, limit):
        """See IPillarSet."""
        if limit is None:
            limit = config.launchpad.default_batch_size
        query = self.build_search_query(text) + """
            /* we order by rank AND name to break ties between pillars with
               the same rank in a consistent fashion, and we add the hard
               LIMIT */
            ORDER BY rank DESC, name
            LIMIT %d
            """ % limit
        cur = cursor()
        cur.execute(query)
        keys = ['type', 'id', 'name', 'title', 'description', 'icon', 'rank']
        # People shouldn't be calling this method with too big limits
        longest_expected = 2 * config.launchpad.default_batch_size
        return shortlist(
            [dict(zip(keys, values)) for values in cur.fetchall()],
            longest_expected=longest_expected)


class PillarName(SQLBase):
    implements(IPillarName)

    _table = 'PillarName'

    name = StringCol(dbName='name', notNull=True, unique=True, alternateID=True)
    product = ForeignKey(foreignKey='Product', dbName='product')
    project = ForeignKey(foreignKey='Project', dbName='project')
    distribution = ForeignKey(foreignKey='Distribution', dbName='distribution')
    active = BoolCol(dbName='active', notNull=True, default=True)

    @property
    def pillar(self):
        if self.distribution is not None:
            return self.distribution
        elif self.project is not None:
            return self.project
        elif self.product is not None:
            return self.product
        else:
            raise AssertionError("Unknown pillar type: %s" % self.name)
