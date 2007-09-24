# Copyright Canonical

__metaclass__ = type

__all__ = [
    'ProjectBugsFeed',
    ]

from canonical.lazr.feed import FeedBase,FeedEntry, MINUTES
from canonical.launchpad.interfaces import IProject

class ProjectBugsFeed(FeedBase):

    usedfor = IProject

    # Will be served as:
    #     $project/latest-bugs.atom, and as
    # XXX    $project/latest-bugs.html, and as
    # XXX    $project/latest-bugs.js
    feed_name = 'latest-bugs'

    max_age = 30 * MINUTES

    def getTitle(self):
        # Title of the whole feed.
        project = self.context
        return "bugs in %s" % self.context.displayname

    def getURL(self):
        # URL to the homepage of the object represented by the feed.
        return canonical_url(self.context, rootsite = "bugs")

    def getItems(self, how_many=None):
        # Items in the feed.  The number of items is configured separately,
        # either globally for Launchpad as a whole, or in the ZCML.
        # If we find we have a requirement for different numbers of items per
        # feed, we'll include it in the class definition.
        if how_many is None:
            return self.context.latestBugs
        else:
            return self.context.latestBugs[:how_many]

    def itemToAtomFeedEntry(self, item):
        bugtask = item
        bug = bugtask.bug

        entry = FeedEntry()
        entry.title = '[%s] %s' % (bug.id, bug.title)
        entry.URL = canonical_url(bugtask, rootsite="bugs")

        # text_to_html will return a subclass of unicode that tells the
        # framework that HTML quoting is taken care of
        entry.content = text_to_html(bug.description)

        entry.date_published = bugtask.datecreated
        entry.date_updated = bug.date_last_updated
        entry.author = bug.owner
        entry.id = entry.URL

        return entry
