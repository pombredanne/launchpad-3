# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Database class for Announcement."""

__metaclass__ = type
__all__ = ['Announcement', ]

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
from canonical.launchpad.interfaces import IAnnouncement

from canonical.launchpad.webapp.authorization import check_permission


class Announcement(SQLBase):
    """A news item. These allow us to generate lists of recent news for
    projects, products and distributions.
    """
    implements(IAnnouncement)

    _defaultOrder = ['-date_announced', '-date_created']

    date_created = UtcDateTimeCol(
        dbName='date_created', notNull=True, default=UTC_NOW)
    date_announced = UtcDateTimeCol(default=None)
    date_updated = UtcDateTimeCol(default=None)
    registrant = ForeignKey(dbName='registrant',
                            foreignKey='Person', notNull=True)
    product = ForeignKey(dbName='product', foreignKey='Product')
    project = ForeignKey(dbName='project', foreignKey='Project')
    distribution = ForeignKey(dbName='distribution', foreignKey='Distribution')
    title = StringCol(notNull=True)
    summary = StringCol(default=None)
    url = StringCol(default=None)
    active = BoolCol(notNull=True, default=True)

    def modify(self, title, summary=None, url=None):
        if self.title != title:
            self.date_updated = UTC_NOW
            self.title = title
        if self.summary != summary:
            self.date_updated = UTC_NOW
            self.summary = summary
        if self.url != url:
            self.date_updated = UTC_NOW
            self.url = url

    @property
    def target(self):
        if self.product is not None:
            return self.product
        elif self.project is not None:
            return self.project
        elif self.distribution is not None:
            return self.distribution

    def retarget(self, product=None, project=None, distribution=None):
        """See IAnnouncement."""
        assert not (product and distribution)
        assert not (product and project)
        assert not (project and distribution)
        assert (product or project or distribution)

        self.product = product
        self.project = project
        self.distribution = distribution

    def set_publication_date(self, publication_date):
        """See IAnnouncement."""
        # figure out the correct date_announced by mapping from the provided
        # publication date to a database value
        if publication_date == 'NOW':
            self.date_announced = UTC_NOW
        elif publication_date == None:
            self.date_announced = None
        else:
            self.date_announced = publication_date

    def erase_permanently(self):
        """See IAnnouncement."""
        Announcement.delete(self.id)

    @property
    def future(self):
        """See IAnnouncement."""
        if self.date_announced is None:
            return True
        return self.date_announced.replace(tzinfo=None) > \
               self.date_announced.utcnow()


class HasAnnouncements:
    """A mixin class for pillars that can have announcements."""

    def announce(self, user, title, summary=None, url=None,
                 publication_date=None):
        """See IHasAnnouncements."""

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
        announcement = Announcement(
            registrant = user,
            title = title,
            summary = summary,
            url = url,
            product = product,
            project = project,
            distribution = distribution
            )

        announcement.set_publication_date(publication_date)
        return announcement

    def getAnnouncement(self, name):
        try:
            announcement_id = int(name)
        except ValueError:
            return None
        return Announcement.get(announcement_id)

    def announcements(self, limit=5):
        """See IHasAnnouncements."""

        # establish whether the user can see all news items, or only the
        # published ones that are past their announcement date
        privileged_user = check_permission('launchpad.Edit', self)

        # create the SQL query, first fixing the anchor project
        clauseTables = []
        query = '1=1 '
        # filter for published news items if necessary
        if not privileged_user:
            query += """ AND
                Announcement.date_announced <= timezone('UTC'::text, now()) AND
                Announcement.active IS TRUE
                """
        if IProduct.providedBy(self):
            if self.project is None:
                query += """ AND
                    Announcement.product = %s""" % sqlvalues(self.id)
            else:
                query += """ AND
                    (Announcement.product = %s OR Announcement.project = %s)
                    """ % sqlvalues(self.id, self.project)
        elif IProject.providedBy(self):
            query += """ AND
                (Announcement.project = %s OR Announcement.product IN
                    (SELECT id FROM Product WHERE project = %s))
                    """ % sqlvalues (self.id, self.id)
        elif IDistribution.providedBy(self):
            query = 'Announcement.distribution = %s' % sqlvalues(self.id)
        else:
            raise AssertionError, 'Unsupported announcement target'
        return Announcement.select(query, limit=limit)



