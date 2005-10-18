# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Karma', 'KarmaSet', 'KarmaAction', 'KarmaActionSet', 'KarmaCache',
           'KarmaCacheSet']

from datetime import datetime, timedelta

import pytz

# Zope interfaces
from zope.interface import implements

# SQLObject imports
from sqlobject import (
    DateTimeCol, ForeignKey, IntCol, StringCol, SQLObjectNotFound)

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces import (
    IKarma, IKarmaAction, IKarmaActionSet, IKarmaCache, IKarmaSet,
    IKarmaCacheSet)
from canonical.lp.dbschema import EnumCol, KarmaActionCategory, KarmaActionName


class Karma(SQLBase):
    """See IKarma."""
    implements(IKarma)

    _table = 'Karma'

    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    action = ForeignKey(dbName='action', foreignKey='KarmaAction', notNull=True)
    datecreated = DateTimeCol(
                    dbName='datecreated', notNull=True, default=UTC_NOW)


class KarmaSet:
    """See IKarmaSet."""
    implements(IKarmaSet)

    def selectByPersonAndAction(self, person, action):
        """See IKarmaSet."""
        query = 'person = %s AND action = %s' % sqlvalues(person.id, action.id)
        return Karma.select(query)

    def getSumByPersonAndCategory(self, person, category):
        """See IKarmaSet."""
        return self._getSumByPerson(person, category)

    def getSumByPerson(self, person):
        """See IKarmaSet."""
        return self._getSumByPerson(person)

    def _getSumByPerson(self, person, category=None):
        """Return the karma value for the given person.

        If <category> is not None, return the value referent to the performed
        actions of that category, only.
        """
        now = datetime.now(pytz.timezone('UTC'))
        catfilter = ''
        if category is not None:
            catfilter = ' AND KarmaAction.category = %s' % sqlvalues(category)

        begin = now - timedelta(30)
        q = ('Karma.action = KarmaAction.id AND Karma.person = %s '
             'AND Karma.datecreated >= %s' % sqlvalues(person.id, begin))
        q += catfilter
        results = KarmaAction.select(q, clauseTables=['Karma'])
        recentpoints = results.sum('points')
        if recentpoints is None:
           recentpoints = 0

        begin = now - timedelta(90)
        end = datetime.now(pytz.timezone('UTC')) - timedelta(30)
        q = ('Karma.action = KarmaAction.id AND Karma.person = %s '
             'AND Karma.datecreated BETWEEN %s AND %s'
             % sqlvalues(person.id, begin, end))
        q += catfilter
        results = KarmaAction.select(q, clauseTables=['Karma'])
        notsorecentpoints = results.sum('points')
        if notsorecentpoints is None:
           notsorecentpoints = 0

        begin = now - timedelta(365)
        end = now - timedelta(90)
        q = ('Karma.action = KarmaAction.id AND Karma.person = %s '
             'AND Karma.datecreated BETWEEN %s AND %s'
             % sqlvalues(person.id, begin, end))
        q += catfilter
        results = KarmaAction.select(q, clauseTables=['Karma'])
        oldpoints = results.sum('points')
        if oldpoints is None:
           oldpoints = 0

        return int(recentpoints + (notsorecentpoints * 0.5) + (oldpoints * 0.2))


class KarmaAction(SQLBase):
    """See IKarmaAction."""
    implements(IKarmaAction)

    _table = 'KarmaAction'
    sortingColumns = ['category', 'name']
    _defaultOrder = sortingColumns

    name = EnumCol(dbName='name', schema=KarmaActionName, alternateID=True)
    category = EnumCol(
                dbName='category', schema=KarmaActionCategory, notNull=True)
    points = IntCol(dbName='points', notNull=True)


class KarmaActionSet:
    """See IKarmaActionSet."""
    implements(IKarmaActionSet)

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
                 'AND Karma.person = %s' % sqlvalues(category, person.id))
        return KarmaAction.select(
                query, clauseTables=['Karma'], distinct=True, orderBy=orderBy)


class KarmaCache(SQLBase):
    """See IKarmaCache."""
    implements(IKarmaCache)

    _table = 'KarmaCache'

    person = ForeignKey(dbName='person', notNull=True)
    category = EnumCol(
                dbName='category', schema=KarmaActionCategory, notNull=True)
    karmavalue = IntCol(dbName='karmavalue', notNull=True)


class KarmaCacheSet:
    """See IKarmaCacheSet."""
    implements(IKarmaCacheSet)

    def new(self, person, category, karmavalue):
        """See IKarmaCacheSet."""
        return KarmaCache(
                personID=person.id, category=category, karmavalue=karmavalue)

    def getByPersonAndCategory(self, person, category, default=None):
        """See IKarmaCacheSet."""
        cache = KarmaCache.selectOneBy(personID=person.id, category=category)
        if cache is None:
            cache = default
        return cache

