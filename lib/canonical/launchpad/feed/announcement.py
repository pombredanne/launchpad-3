# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Announcement feed (syndication) views."""

__metaclass__ = type

__all__ = [
    'AnnouncementsFeed',
    'TargetAnnouncementsFeed',
    ]


import cgi
from zope.component import getUtility

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.interfaces import (
    IAnnouncementSet, IDistribution, IHasAnnouncements, IProduct, IProject)
from canonical.launchpad.interfaces import IFeedsApplication
from canonical.lazr.feed import (
    FeedBase, FeedEntry, FeedPerson, FeedTypedData)


class AnnouncementsFeedBase(FeedBase):
    """Abstract class for announcement feeds."""

    feedname = "announcements"

    def normalizedUrl(self, rootsite=None):
        url = canonical_url(self.context, rootsite=rootsite)
        # canonical_url has a trailing '/' when there is no path information
        # but does not if a path is present.  If a trailing '/' doesn't exist,
        # add it on so the constructed URL will be correct for all cases.
        if not url.endswith('/'):
            url += '/'
        return url

    @property
    def alternate_url(self):
        """See `IFeed`."""
        return "%s+announcements" % self.normalizedUrl(rootsite="mainsite")

    def entryTitle(self, announcement):
        """Return the title for the announcement.

        Override in each base class.
        """
        raise NotImplementedError

    def itemToFeedEntry(self, announcement):
        """See `IFeed`."""
        title = self.entryTitle(announcement)
        entry_extra_path = "/+announcement/%d" % announcement.id
        entry_alternate_url = "%s%s" % (
            canonical_url(announcement.target, rootsite=self.rootsite),
            entry_extra_path)
        entry = FeedEntry(title=title,
                          link_alternate=entry_alternate_url,
                          date_created=announcement.date_created,
                          date_updated=announcement.date_updated,
                          date_published=announcement.date_announced,
                          authors=[FeedPerson(
                                    announcement.registrant,
                                    rootsite="mainsite")],
                          content=FeedTypedData(cgi.escape(announcement.summary)))
        return entry

    @property
    def url(self):
        """See `IFeed`."""
        return "%s%s.%s" % (
            self.normalizedUrl(), self.feedname, self.format)


class AnnouncementsFeed(AnnouncementsFeedBase):
    """Publish an Atom feed of all public announcements in Launchpad."""

    usedfor = IFeedsApplication

    def getItems(self):
        """See `IFeed`."""
        # The quantity is defined in FeedBase or config file.
        items = getUtility(IAnnouncementSet).announcements(
            limit=self.quantity)
        # Convert the items into their feed entry representation.
        items = [self.itemToFeedEntry(item) for item in items]
        return items

    def entryTitle(self, announcement):
        return FeedTypedData('[%s] %s' % (
                announcement.target.name, announcement.title))

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


class TargetAnnouncementsFeed(AnnouncementsFeedBase):
    """Publish an Atom feed of all announcements.

    Used for a project, product, or distribution.
    """

    usedfor = IHasAnnouncements

    def getItems(self):
        """See `IFeed`."""
        # The quantity is defined in FeedBase or config file.
        items = self.context.announcements(limit=self.quantity)
        # Convert the items into their feed entry representation.
        items = [self.itemToFeedEntry(item) for item in items]
        return items

    def entryTitle(self, announcement):
        return FeedTypedData(announcement.title)

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
