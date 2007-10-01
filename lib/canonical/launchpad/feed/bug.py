# Copyright Canonical

__metaclass__ = type

__all__ = [
    'PersonBugsFeed',
    'ProductBugsFeed',
    'SearchBugs',
    ]

import cgi
from datetime import datetime
from zope.app.pagetemplate import ViewPageTemplateFile

from canonical.lazr.feed import (
    FeedBase, FeedEntry, FeedPerson, FeedTypedData, MINUTES)

from canonical.lp import dbschema
from canonical.launchpad import helpers
from canonical.launchpad.interfaces import (
    IPerson, IProduct)
from canonical.launchpad.webapp import canonical_url, LaunchpadFormView
from zope.app.pagetemplate import ViewPageTemplateFile
from canonical.launchpad.webapp.publisher import LaunchpadView
from canonical.launchpad.browser.bugtask import BugTaskView
from canonical.launchpad.browser import (
    BugTasksAndNominationsView, BugsBugTaskSearchListingView,
    BugTaskSearchListingView,
    PersonRelatedBugsView)

class BugFeedContentView(LaunchpadView):
    template = ViewPageTemplateFile('templates/bug.pt')
    def getBugCommentsForDisplay(self):
        bug_task_view = BugTaskView(self.context.bugtasks[0], self.request)
        return bug_task_view.getBugCommentsForDisplay()

class ProductBugsFeed(FeedBase):

    # XXX, bac - This variable is currently not used.
    usedfor = IProduct

    # Will be served as:
    #     $product/latest-bugs.atom, and as
    # XXX    $product/latest-bugs.html, and as
    # XXX    $product/latest-bugs.js
    #feed_name = 'latest-bugs'
    feed_name = 'latest-bugs.atom'

    max_age = 30 * MINUTES

    def getTitle(self):
        # Title of the whole feed.
        return "Bugs in %s" % self.context.displayname

    def getURL(self):
        # URL to the homepage of the object represented by the feed.
        #return canonical_url(self.context, rootsite = "bugs")
        return "%s/%s" % (canonical_url(self.context), self.feed_name)

    def getItems(self, quantity=5):
        # Items in the feed.  The number of items is configured separately,
        # either globally for Launchpad as a whole, or in the ZCML.
        # If we find we have a requirement for different numbers of items per
        # feed, we'll include it in the class definition.
        if self.items is None:
            items = self.context.getLatestBugTasks(quantity=quantity)
            self.items = [self.itemToFeedEntry(item) for item in items]
        return self.items

    def getLogo(self):
        return "http://launchpad.dev/+icing/app-bugs.gif"

    def itemToFeedEntry(self, item):
        bugtask = item
        bug = bugtask.bug
        title = FeedTypedData('[%s] %s' % (bug.id, bug.title))
        url = canonical_url(bugtask, rootsite="bugs")
        content_view = BugFeedContentView(bug, self.request)
        entry = FeedEntry(title = title,
                          id_ = url,
                          link_alternate = url,
                          date_updated = bug.date_last_updated,
                          date_published = bugtask.datecreated,
                          authors = [FeedPerson(bug.owner)],
                          content = FeedTypedData(content_view.render(),
                                                  content_type="xhtml"))
        return entry


class PersonBugsFeed(FeedBase, PersonRelatedBugsView):

    usedfor = IPerson

    # Will be served as:
    #     $product/latest-bugs.atom, and as
    # XXX    $product/latest-bugs.html, and as
    # XXX    $product/latest-bugs.js
    #feed_name = 'latest-bugs'
    feed_name = 'latest-bugs.atom'

    max_age = 30 * MINUTES

    def getTitle(self):
        # Title of the whole feed.
        return "Bugs for %s" % self.context.displayname

    def getURL(self):
        # URL to the homepage of the object represented by the feed.
        #return canonical_url(self.context, rootsite = "bugs")
        return "%s/%s" % (canonical_url(self.context), self.feed_name)

    def getItems(self, quantity=5):
        # Items in the feed.  The number of items is configured separately,
        # either globally for Launchpad as a whole, or in the ZCML.
        # If we find we have a requirement for different numbers of items per
        # feed, we'll include it in the class definition.
        if self.items is None:
            #items = self.context.getLatestBugs(quantity=quantity)
            items = self.search()
            self.items = [self.itemToFeedEntry(item) for item in items]
        return self.items

    def getLogo(self):
        return "http://launchpad.dev/+icing/app-bugs.gif"

    def itemToFeedEntry(self, item):
        bugtask = item
        bug = bugtask.bug
        title = FeedTypedData('[%s] %s' % (bug.id, bug.title))
        url = canonical_url(bugtask, rootsite="bugs")
        content_view = BugFeedContentView(bug, self.request)
        entry = FeedEntry(title = title,
                          id_ = url,
                          link_alternate = url,
                          date_updated = bug.date_last_updated,
                          date_published = bugtask.datecreated,
                          authors = [FeedPerson(bug.owner)],
                          content = FeedTypedData(content_view.render(),
                                                  content_type="xhtml"))
        return entry


class SearchBugs(FeedBase):

    # Will be served as:
    #     $product/latest-bugs.atom, and as
    # XXX    $product/latest-bugs.html, and as
    # XXX    $product/latest-bugs.js
    #feed_name = 'latest-bugs'
    feed_name = 'search-bugs.atom'

    max_age = 30 * MINUTES

    def initialize(self):
        self.task_search_listing_view = BugsBugTaskSearchListingView(self.context, self.request)
        self.task_search_listing_view.initialize()
        query_string = self.request.get('QUERY_STRING')

    def search(self, searchtext=None, context=None, extra_params=None):
        """Return an ITableBatchNavigator for the GET search criteria.

        If :searchtext: is None, the searchtext will be gotten from the
        request.

        :extra_params: is a dict that provides search params added to the
        search criteria taken from the request. Params in :extra_params: take
        precedence over request params.
        """
        #search_params = self.task_search_listing_view._getDefaultSearchParams()
        #tasks =  self.task_search_listing_view.
        results =  self.task_search_listing_view.search(searchtext, context, extra_params)
        items = results.getBugListingItems()
        return items

    def getTitle(self):
        # Title of the whole feed.
        return "Bugs from custom search."

    def getURL(self):
        # URL to the homepage of the object represented by the feed.
        #return canonical_url(self.context, rootsite = "bugs")
        return "%s/%s" % (canonical_url(self.context), self.feed_name)

    def getItems(self, quantity=5):
        # Items in the feed.  The number of items is configured separately,
        # either globally for Launchpad as a whole, or in the ZCML.
        # If we find we have a requirement for different numbers of items per
        # feed, we'll include it in the class definition.
        if self.items is None:
            #items = self.context.getLatestBugs(quantity=quantity)
            items = self.search()
            self.items = [self.itemToFeedEntry(item) for item in items]
        return self.items

    def getLogo(self):
        return "http://launchpad.dev/+icing/app-bugs.gif"

    def itemToFeedEntry(self, item):
        bugtask = item
        bug = bugtask.bug
        title = FeedTypedData('[%s] %s' % (bug.id, bug.title))
        url = canonical_url(bugtask, rootsite="bugs")
        content_view = BugFeedContentView(bug, self.request)
        entry = FeedEntry(title = title,
                          id_ = url,
                          link_alternate = url,
                          date_updated = bug.date_last_updated,
                          date_published = bugtask.datecreated,
                          authors = [FeedPerson(bug.owner)],
                          content = FeedTypedData(content_view.render(),
                                                  content_type="xhtml"))
        return entry
