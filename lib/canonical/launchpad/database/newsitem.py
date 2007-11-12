# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Database class for NewsItem."""

__metaclass__ = type
__all__ = ['NewsItem', ]

import operator
from sqlobject import (
    ForeignKey, StringCol, BoolCol, SQLMultipleJoin, SQLRelatedJoin,
    SQLObjectNotFound, AND)
from zope.interface import implements
from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IProduct, IProject, IDistribution)

from canonical.cachedproperty import cachedproperty
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import quote, SQLBase, sqlvalues
from canonical.launchpad.interfaces import INewsItem


class NewsItem(SQLBase):
    """A news item. These allow us to generate lists of recent news for
    projects, products and distributions.
    """

    date_created = UtcDateTimeCol(
        dbName='date_created', notNull=True, default=UTC_NOW)
    date_announced = UtcDateTimeCol(
        dbName='date_announced', default=UTC_NOW)
    registrant = ForeignKey(dbName='registrant',
                            foreignKey='Person', notNull=True)
    product = ForeignKey(dbName='product', foreignKey='Product', notNull=True)
    project = ForeignKey(dbName='project', foreignKey='Project', notNull=True)
    distribution = ForeignKey(dbName='distribution',
                              foreignKey='distribution', notNull=True)
    title = StringCol(notNull=True)
    summary = StringCol(default=None)
    url = StringCol(default=None)
    active = BoolCol(notNull=True, default=True)

    @property
    def target(self):
        if self.product is not None:
            return self.product
        elif self.project is not None:
            return self.project
        elif self.distribution is not None:
            return self.distribution


class HasNewsItems:
    """A mixin class for pillars that can have announcements."""

    def announce(self, user, title, summary=None, url=None,
                 date_announced=None):
        """See IHasNewsItems."""

        # establish the appropriate target
        project = product = distribution = None
        if IProduct.providedBy(self):
            product = self
        elif IProject.providedBy(self):
            project = self
        elif IDistribution.providedBy(self):
            distribution = self
        else:
            raise AssertionError, 'Unsupported announcement target'

        # create the news item
        return NewsItem(
            registrant = user,
            title = title,
            summary = summary,
            url = url,
            date_announced = date_announced,
            product = product,
            project = project,
            distribution = distribution
            )

