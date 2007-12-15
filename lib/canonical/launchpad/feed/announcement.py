# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Announcement feed (syndication) views."""

__metaclass__ = type

__all__ = [
    'AnnouncementsFeed',
    'TargetAnnouncementsFeed',
    ]

from zope.component import getUtility

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.interfaces import (
    IAnnouncementSet, IDistribution, IHasAnnouncements, IProduct, IProject)
from canonical.launchpad.interfaces import IFeedsApplication
from canonical.lazr.feed import (
    FeedBase, FeedEntry, FeedPerson, FeedTypedData)


class AnnouncementsFeed(FeedBase):
    """Publish an Atom feed of all public announcements in Launchpad."""

    usedfor = IFeedsApplication
    feedname = "announcements"

    def getItems(self):
        """See `IFeed`."""
        # The quantity is defined in FeedBase or config file.
        items = getUtility(IAnnouncementSet).announcements(limit=self.quantity)
        # Convert the items into their feed entry representation.
        items = [self.itemToFeedEntry(item) for item in items]
        return items

    def itemToFeedEntry(self, announcement):
        """See `IFeed`."""
        title = FeedTypedData('[%s] %s' % (
            announcement.target.name, announcement.title))
        id = 'tag:launchpad.net,%s:/+announcements/%d' % (
                announcement.date_created.date().isoformat(),
                announcement.id)
        entry = FeedEntry(title=title,
                          id_=id,
                          link_alternate=announcement.url,
                          date_updated=announcement.date_updated,
                          date_published=announcement.date_announced,
                          authors=[FeedPerson(
                                    announcement.registrant,
                                    rootsite="mainsite")],
                          content=FeedTypedData(announcement.summary))
        return entry

    @property
    def title(self):
        """See `IFeed`."""
        return "Announcements published via Launchpad"

    @property
    def logo(self):
        """See `IFeed`."""
        url = '/@@/launchpad-logo'
        return self.site_url + url

    @property
    def icon(self):
        """See `IFeed`."""
        url = '/@@/launchpad'
        return self.site_url + url

    @property
    def url(self):
        """See `IFeed`."""
        return "%s%s.%s" % (
            canonical_url(self.context), self.feedname, self.format)


class TargetAnnouncementsFeed(FeedBase):
    """Publish an Atom feed of all announcements for a project."""

    usedfor = IHasAnnouncements
    feedname = "announcements"

    def getItems(self):
        """See `IFeed`."""
        # The quantity is defined in FeedBase or config file.
        items = self.context.announcements(limit=self.quantity)
        # Convert the items into their feed entry representation.
        items = [self.itemToFeedEntry(item) for item in items]
        return items

    def itemToFeedEntry(self, announcement):
        """See `IFeed`."""
        title = FeedTypedData(announcement.title)
        id = 'tag:launchpad.net,%s:/+announcements/%d' % (
                announcement.date_created.date().isoformat(),
                announcement.id)
        entry = FeedEntry(title=title,
                          id_=id,
                          link_alternate=announcement.url,
                          date_updated=announcement.date_updated,
                          date_published=announcement.date_announced,
                          authors=[FeedPerson(
                                    announcement.registrant,
                                    rootsite="mainsite")],
                          content=FeedTypedData(announcement.summary))
        return entry

    @property
    def title(self):
        """See `IFeed`."""
        return "%s Announcements" % self.context.displayname

    @property
    def logo(self):
        """See `IFeed`."""
        if self.context.logo is not None:
            return self.context.logo.getURL()
        elif IProject.providedBy(self.context):
            url = '/@@/project-logo'
        elif IProduct.providedBy(self.context):
            url = '/@@/product-logo'
        elif IDistribution.providedBy(self.context):
            url = '/@@/distribution-logo'
        return self.site_url + url

    @property
    def icon(self):
        """See `IFeed`."""
        if self.context.icon is not None:
            return self.context.icon.getURL()
        elif IProject.providedBy(self.context):
            url = '/@@/project'
        elif IProduct.providedBy(self.context):
            url = '/@@/product'
        elif IDistribution.providedBy(self.context):
            url = '/@@/distribution'
        return self.site_url + url

    @property
    def url(self):
        """See `IFeed`."""
        return "%s/%s.%s" % (
            canonical_url(self.context), self.feedname, self.format)

