# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Database classes for project news and announcement."""

__metaclass__ = type
__all__ = [
    'Announcement',
    'AnnouncementSet',
    'HasAnnouncements',
    'MakesAnnouncements',
    ]

import pytz, datetime
from sqlobject import BoolCol, ForeignKey, SQLObjectNotFound, StringCol
from zope.interface import implements

from canonical.launchpad.interfaces import (
    IAnnouncement, IAnnouncementSet, IDistribution, IProduct, IProject)

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase, sqlvalues


class Announcement(SQLBase):
    """A news item. These allow us to generate lists of recent news for
    projects, products and distributions.
    """
    implements(IAnnouncement)

    _defaultOrder = ['-date_announced', '-date_created']

    date_created = UtcDateTimeCol(
        dbName='date_created', notNull=True, default=UTC_NOW)
    date_announced = UtcDateTimeCol(default=None)
    date_last_modified = UtcDateTimeCol(
        dbName='date_updated', default=None)
    registrant = ForeignKey(
        dbName='registrant', foreignKey='Person', notNull=True)
    product = ForeignKey(dbName='product', foreignKey='Product')
    project = ForeignKey(dbName='project', foreignKey='Project')
    distribution = ForeignKey(
        dbName='distribution', foreignKey='Distribution')
    title = StringCol(notNull=True)
    summary = StringCol(default=None)
    url = StringCol(default=None)
    active = BoolCol(notNull=True, default=True)

    def modify(self, title, summary, url):
        if self.title != title:
            self.title = title
            self.date_last_modified = UTC_NOW
        if self.summary != summary:
            self.summary = summary
            self.date_last_modified = UTC_NOW
        if self.url != url:
            self.url = url
            self.date_last_modified = UTC_NOW

    @property
    def target(self):
        if self.product is not None:
            return self.product
        elif self.project is not None:
            return self.project
        elif self.distribution is not None:
            return self.distribution
        else:
            raise AssertionError, 'Announcement has no obvious target'

    def retarget(self, target):
        """See `IAnnouncement`."""
        if IProduct.providedBy(target):
            self.product = target
            self.distribution = None
            self.project = None
        elif IDistribution.providedBy(target):
            self.distribution = target
            self.project = None
            self.product = None
        elif IProject.providedBy(target):
            self.project = target
            self.distribution = None
            self.product = None
        else:
            raise AssertionError, 'Unknown target'
        self.date_last_modified = UTC_NOW

    def retract(self):
        """See `IAnnouncement`."""
        self.active = False
        self.date_last_modified = UTC_NOW

    def set_publication_date(self, publication_date):
        """See `IAnnouncement`."""
        self.date_announced = publication_date
        self.date_last_modified = None
        self.active = True

    @property
    def future(self):
        """See `IAnnouncement`."""
        if self.date_announced is None:
            return True
        return self.date_announced > \
               datetime.datetime.utcnow().replace(tzinfo=pytz.utc)

    @property
    def published(self):
        """See `IAnnouncement`."""
        if self.active is False:
            return False
        return not self.future


class HasAnnouncements:
    """A mixin class for pillars that can have announcements."""

    def getAnnouncement(self, id):
        try:
            announcement_id = int(id)
        except ValueError:
            return None
        try:
            announcement = Announcement.get(announcement_id)
        except SQLObjectNotFound:
            return None
        if announcement.target.name != self.name:
            return None
        return announcement

    def announcements(self, limit=5, published_only=True):
        """See IHasAnnouncements."""

        # Create the SQL query.
        clauseTables = []
        query = '1=1 '
        # Filter for published news items if necessary.
        if published_only:
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
            query += ' AND Announcement.distribution = %s' % sqlvalues(self.id)
        elif IAnnouncementSet.providedBy(self):
            # There is no need to filter for pillar if we are looking for
            # all announcements.
            pass
        else:
            raise AssertionError, 'Unsupported announcement target'
        return Announcement.select(query, limit=limit)


class MakesAnnouncements(HasAnnouncements):

    def announce(self, user, title, summary=None, url=None,
                 publication_date=None):
        """See IHasAnnouncements."""

        # We establish the appropriate target property.
        project = product = distribution = None
        if IProduct.providedBy(self):
            product = self
        elif IProject.providedBy(self):
            project = self
        elif IDistribution.providedBy(self):
            distribution = self
        else:
            raise AssertionError, 'Unsupported announcement target'

        # Create the announcement in the database.
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


class AnnouncementSet(HasAnnouncements):
    """The set of all announcements across all pillars."""

    implements(IAnnouncementSet)

    displayname = 'Launchpad-hosted'
    title = 'Launchpad'



