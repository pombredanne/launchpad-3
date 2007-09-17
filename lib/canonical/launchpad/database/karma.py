# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'Karma',
    'KarmaAction',
    'KarmaActionSet',
    'KarmaCache',
    'KarmaCacheManager',
    'KarmaTotalCache',
    'KarmaCategory',
    'KarmaContextMixin',
    ]

from zope.interface import implements

from sqlobject import (
    ForeignKey, IntCol, StringCol, SQLObjectNotFound,
    SQLMultipleJoin)
from sqlobject.sqlbuilder import AND

from canonical.database.sqlbase import SQLBase, sqlvalues, cursor
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces import (
    IKarma, IKarmaAction, IKarmaActionSet, IKarmaCache, IKarmaCategory,
    IKarmaTotalCache, IKarmaContext, IProduct, IDistribution,
    IKarmaCacheManager, NotFoundError, IProject)


class Karma(SQLBase):
    """See IKarma."""
    implements(IKarma)

    _table = 'Karma'
    _defaultOrder = ['action', 'id']

    person = ForeignKey(
        dbName='person', foreignKey='Person', notNull=True)
    action = ForeignKey(
        dbName='action', foreignKey='KarmaAction', notNull=True)
    product = ForeignKey(
        dbName='product', foreignKey='Product', notNull=False)
    distribution = ForeignKey(
        dbName='distribution', foreignKey='Distribution', notNull=False)
    sourcepackagename = ForeignKey(
        dbName='sourcepackagename', foreignKey='SourcePackageName',
        notNull=False)
    datecreated = UtcDateTimeCol(
        dbName='datecreated', notNull=True, default=UTC_NOW)


class KarmaAction(SQLBase):
    """See IKarmaAction."""
    implements(IKarmaAction)

    _table = 'KarmaAction'
    sortingColumns = ['category', 'name']
    _defaultOrder = sortingColumns

    name = StringCol(notNull=True, alternateID=True)
    title = StringCol(notNull=True)
    summary = StringCol(notNull=True)
    category = ForeignKey(dbName='category', foreignKey='KarmaCategory',
        notNull=True)
    points = IntCol(dbName='points', notNull=True)


class KarmaActionSet:
    """See IKarmaActionSet."""
    implements(IKarmaActionSet)

    def __iter__(self):
        return iter(KarmaAction.select())

    def getByName(self, name, default=None):
        """See IKarmaActionSet."""
        try:
            return KarmaAction.byName(name)
        except SQLObjectNotFound:
            return default

    def selectByCategory(self, category):
        """See IKarmaActionSet."""
        return KarmaAction.selectBy(category=category)

    def selectByCategoryAndPerson(self, category, person, orderBy=None):
        """See IKarmaActionSet."""
        if orderBy is None:
            orderBy = KarmaAction.sortingColumns
        query = ('KarmaAction.category = %s '
                 'AND Karma.action = KarmaAction.id '
                 'AND Karma.person = %s' % sqlvalues(category.id, person.id))
        return KarmaAction.select(
                query, clauseTables=['Karma'], distinct=True, orderBy=orderBy)


class KarmaCache(SQLBase):
    """See IKarmaCache."""
    implements(IKarmaCache)

    _table = 'KarmaCache'
    _defaultOrder = ['category', 'id']

    person = ForeignKey(
        dbName='person', foreignKey='Person', notNull=True)
    category = ForeignKey(
        dbName='category', foreignKey='KarmaCategory', notNull=False)
    karmavalue = IntCol(
        dbName='karmavalue', notNull=True)
    product = ForeignKey(
        dbName='product', foreignKey='Product', notNull=False)
    project = ForeignKey(
        dbName='project', foreignKey='Project', notNull=False)
    distribution = ForeignKey(
        dbName='distribution', foreignKey='Distribution', notNull=False)
    sourcepackagename = ForeignKey(
        dbName='sourcepackagename', foreignKey='SourcePackageName',
        notNull=False)


class KarmaCacheManager:
    """See IKarmaCacheManager."""
    implements(IKarmaCacheManager)

    def new(self, value, person_id, category_id, product_id=None, distribution_id=None,
            sourcepackagename_id=None, project_id=None):
        """See IKarmaCacheManager."""
        return KarmaCache(
            karmavalue=value, person=person_id, category=category_id,
            product=product_id, distribution=distribution_id,
            sourcepackagename=sourcepackagename_id, project=project_id)

    def updateKarmaValue(self, value, person_id, category_id, product_id=None,
                         distribution_id=None, sourcepackagename_id=None,
                         project_id=None):
        """See IKarmaCacheManager."""
        entry = self._getEntry(
            person_id=person_id, category_id=category_id, product_id=product_id,
            distribution_id=distribution_id, project_id=project_id,
            sourcepackagename_id=sourcepackagename_id)
        if entry is None:
            raise NotFoundError("KarmaCache not found: %s" % vars())
        else:
            entry.karmavalue = value
            entry.syncUpdate()

    def _getEntry(self, person_id, category_id, product_id=None, distribution_id=None,
                  sourcepackagename_id=None, project_id=None):
        """Return the KarmaCache entry with the given arguments.

        Return None if it's not found.
        """
        # Can't use selectBy() because product/distribution/sourcepackagename
        # may be None.
        query = AND(
            KarmaCache.q.personID == person_id,
            KarmaCache.q.categoryID == category_id,
            KarmaCache.q.productID == product_id,
            KarmaCache.q.projectID == project_id,
            KarmaCache.q.distributionID == distribution_id,
            KarmaCache.q.sourcepackagenameID == sourcepackagename_id)
        return KarmaCache.selectOne(query)


class KarmaTotalCache(SQLBase):
    """A cached value of the total of a person's karma (all categories)."""
    implements(IKarmaTotalCache)

    _table = 'KarmaTotalCache'
    _defaultOrder = ['id']

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    karma_total = IntCol(dbName='karma_total', notNull=True)


class KarmaCategory(SQLBase):
    """See IKarmaCategory."""
    implements(IKarmaCategory)

    _defaultOrder = ['title', 'id']

    name = StringCol(notNull=True, alternateID=True)
    title = StringCol(notNull=True)
    summary = StringCol(notNull=True)

    karmaactions = SQLMultipleJoin(
        'KarmaAction', joinColumn='category', orderBy='name')


class KarmaContextMixin:
    """A mixin to be used by classes implementing IKarmaContext.

    This would be better as an adapter for Product and Distribution, but a
    mixin should be okay for now.
    """

    implements(IKarmaContext)

    def getTopContributorsGroupedByCategory(self, limit=None):
        """See IKarmaContext."""
        contributors_by_category = {}
        for category in KarmaCategory.select():
            results = self.getTopContributors(category=category, limit=limit)
            if results:
                contributors_by_category[category] = results
        return contributors_by_category

    def getTopContributors(self, category=None, limit=None):
        """See IKarmaContext."""
        from canonical.launchpad.database.person import Person
        if IProduct.providedBy(self):
            where_clause = "product = %d" % self.id
        elif IDistribution.providedBy(self):
            where_clause = "distribution = %d" % self.id
        elif IProject.providedBy(self):
            where_clause = "project = %d" % self.id
        else:
            raise AssertionError(
                "Not a product, project or distribution: %r" % self)

        if category is not None:
            category_filter = " AND category = %s" % sqlvalues(category)
        else:
            category_filter = " AND category IS NULL"
        if limit is not None:
            limit_filter = " LIMIT %d" % limit
        query = """
            SELECT person, karmavalue
            FROM KarmaCache
            WHERE %(where_clause)s
            %(category_filter)s
            ORDER BY karmavalue DESC
            %(limit)s
            """ % {'where_clause': where_clause, 'limit': limit_filter,
                   'category_filter': category_filter}

        cur = cursor()
        cur.execute(query)
        return [(Person.get(person_id), karmavalue)
                for person_id, karmavalue in cur.fetchall()]

