# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Database class for NewsItem."""

__metaclass__ = type
__all__ = ['NewsItem', ]

import operator
import time, pytz, datetime
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

from canonical.launchpad.webapp.authorization import check_permission


class NewsItem(SQLBase):
    """A news item. These allow us to generate lists of recent news for
    projects, products and distributions.
    """
    implements(INewsItem)

    _defaultOrder = ['-date_announced', '-date_created']

    date_created = UtcDateTimeCol(
        dbName='date_created', notNull=True, default=UTC_NOW)
    date_announced = UtcDateTimeCol(
        dbName='date_announced', default=UTC_NOW)
    registrant = ForeignKey(dbName='registrant',
                            foreignKey='Person', notNull=True)
    product = ForeignKey(dbName='product', foreignKey='Product')
    project = ForeignKey(dbName='project', foreignKey='Project')
    distribution = ForeignKey(dbName='distribution', foreignKey='Distribution')
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

    @property
    def future(self):
        if self.date_announced is None:
            return True
        return self.date_announced.replace(tzinfo=None) > \
               self.date_announced.utcnow()


class HasNewsItems:
    """A mixin class for pillars that can have announcements."""

    def announce(self, user, title, summary=None, url=None,
                 publication_date=None):
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

        # figure out the correct date_announced by mapping from the provided
        # publication date to a database value
        if publication_date == 'NOW':
            date_announced = UTC_NOW
        elif publication_date == None:
            date_announced = None
        else:
            date_announced = publication_date

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

    def announcements(self, limit=5):
        """See IHasNewsItems."""

        # establish whether the user can see all news items, or only the
        # published ones that are past their announcement date
        privileged_user = check_permission('launchpad.Edit', self)

        # create the SQL query, first fixing the anchor project
        clauseTables = []
        query = '1=1 '
        # filter for published news items if necessary
        if not privileged_user:
            query += """ AND
                NewsItem.date_announced <= timezone('UTC'::text, now()) AND
                NewsItem.active IS TRUE
                """
        if IProduct.providedBy(self):
            if self.project is None:
                query += """ AND
                    NewsItem.product = %s""" % sqlvalues(self.id)
            else:
                query += """ AND
                    (NewsItem.product = %s OR NewsItem.project = %s)
                    """ % sqlvalues(self.id, self.project)
        elif IProject.providedBy(self):
            query += """ AND
                (NewsItem.project = %s OR NewsItem.product IN
                    (SELECT id FROM Product WHERE project = %s))
                    """ % sqlvalues (self.id, self.id)
        elif IDistribution.providedBy(self):
            query = 'NewsItem.distribution = %s' % sqlvalues(self.id)
        else:
            raise AssertionError, 'Unsupported announcement target'
        return NewsItem.select(query, limit=limit)



