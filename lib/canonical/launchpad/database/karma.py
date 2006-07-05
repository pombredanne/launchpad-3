# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'Karma',
    'KarmaAction',
    'KarmaActionSet',
    'KarmaCache',
    'KarmaTotalCache',
    'KarmaCategory',
    ]

# Zope interfaces
from zope.interface import implements

# SQLObject imports
from sqlobject import (
    DateTimeCol, ForeignKey, IntCol, StringCol, SQLObjectNotFound,
    SQLMultipleJoin)

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces import (
    IKarma, IKarmaAction, IKarmaActionSet, IKarmaCache, IKarmaCategory,
    IKarmaTotalCache)


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
    datecreated = DateTimeCol(
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
        return KarmaAction.selectBy(categoryID=category.id)

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
        dbName='person', notNull=True)
    category = ForeignKey(
        dbName='category', foreignKey='KarmaCategory', notNull=True)
    karmavalue = IntCol(
        dbName='karmavalue', notNull=True)
    product = ForeignKey(
        dbName='product', foreignKey='Product', notNull=False)
    distribution = ForeignKey(
        dbName='distribution', foreignKey='Distribution', notNull=False)
    sourcepackagename = ForeignKey(
        dbName='sourcepackagename', foreignKey='SourcePackageName',
        notNull=False)


class KarmaTotalCache(SQLBase):
    """A cached value of the total of a person's karma (all categories)."""
    implements(IKarmaTotalCache)

    _table = 'KarmaTotalCache'
    _defaultOrder = ['id']

    person = ForeignKey(dbName='person', notNull=True)
    karma_total = IntCol(dbName='karma_total', notNull=True)


class KarmaCategory(SQLBase):
    """See IKarmaCategory."""
    implements(IKarmaCategory)

    _defaultOrder = ['title', 'id']

    name = StringCol(notNull=True, alternateID=True)
    title = StringCol(notNull=True)
    summary = StringCol(notNull=True)

    karmaactions = SQLMultipleJoin('KarmaAction', joinColumn='category',
        orderBy='name')

