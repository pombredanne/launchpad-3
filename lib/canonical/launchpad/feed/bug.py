# Copyright Canonical

__metaclass__ = type

__all__ = [
    'ProductBugsFeed',
    ]

from datetime import datetime

from canonical.lazr.feed import FeedBase,FeedEntry, MINUTES
from canonical.launchpad.interfaces import IProduct
from canonical.launchpad.webapp import canonical_url

class ProductBugsFeed(FeedBase):

    usedfor = IProduct

    # Will be served as:
    #     $product/latest-bugs.atom, and as
    # XXX    $product/latest-bugs.html, and as
    # XXX    $product/latest-bugs.js
    feed_name = 'latest-bugs'

    max_age = 30 * MINUTES

    def getTitle(self):
        # Title of the whole feed.
        product = self.context
        return "Bugs in %s" % product.displayname

    def getURL(self):
        # URL to the homepage of the object represented by the feed.
        return canonical_url(self.context, rootsite = "bugs")

    def getItems(self, quantity=5):
        # Items in the feed.  The number of items is configured separately,
        # either globally for Launchpad as a whole, or in the ZCML.
        # If we find we have a requirement for different numbers of items per
        # feed, we'll include it in the class definition.
        #import pdb; pdb.set_trace(); # DO NOT COMMIT
        items = self.context.getLatestBugTasks(quantity=quantity)
        return [self.itemToFeedEntry(item) for item in items]

    def itemToFeedEntry(self, item):
        bugtask = item
        bug = bugtask.bug

        entry = FeedEntry()
        entry.title = '[%s] %s' % (bug.id, bug.title)
        entry.URL = canonical_url(bugtask, rootsite="bugs")

        # text_to_html will return a subclass of unicode that tells the
        # framework that HTML quoting is taken care of
        ###entry.content = text_to_html(bug.description)
        entry.content = bug.description

        entry.date_published = bugtask.datecreated
        #entry.date_updated = bug.date_last_updated
        entry.date_updated = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        entry.author = bug.owner
        entry.id_ = entry.URL

        return entry
