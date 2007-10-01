# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Bug feed (syndication) views."""

__metaclass__ = type

__all__ = [
    'PersonBugsFeed',
    'ProjectProductBugsFeed',
    'SearchBugs',
    ]

import cgi
from datetime import datetime

from zope.app.pagetemplate import ViewPageTemplateFile

from canonical.lazr.feed import (
    FeedBase, FeedEntry, FeedPerson, FeedTypedData, MINUTES)
from canonical.launchpad.webapp import canonical_url, LaunchpadFormView
from zope.app.pagetemplate import ViewPageTemplateFile
from canonical.launchpad.webapp.publisher import LaunchpadView
from canonical.launchpad.browser.bugtask import BugTaskView
from canonical.launchpad.browser import (
    BugTasksAndNominationsView, BugsBugTaskSearchListingView,
    BugTaskSearchListingView,
    PersonRelatedBugsView)


class BugFeedContentView(LaunchpadView):
    """View for a bug feed contents."""

    short_template = ViewPageTemplateFile('templates/bug.pt')
    long_template = ViewPageTemplateFile('templates/bug-verbose.pt')

    def __init__(self, context, request, verbose=False):
        super(BugFeedContentView, self).__init__(context, request)
        self.verbose = verbose

    def getBugCommentsForDisplay(self):
        bug_task_view = BugTaskView(self.context.bugtasks[0], self.request)
        return bug_task_view.getBugCommentsForDisplay()

    def render(self):
        if self.verbose:
            return self.long_template()
        else:
            return self.short_template()


class BugsFeedBase(FeedBase):
    """Abstract class for bug feeds."""

    max_age = 30 * MINUTES
    verbose = False

    def getURL(self):
        """Get the identifying URL for the feed."""
        return "%s/%s" % (canonical_url(self.context), self.feed_name)

    def getLogo(self):
        return "http://launchpad.dev/+icing/app-bugs.gif"

    def getItems(self, quantity=5):
        """Get the items for the feed, limited by `quantity`.

        The result is assigned to self.items for caching.
        """
        if self.items is None:
            items = self.getRawItems(quantity)
            self.items = [self.itemToFeedEntry(item) for item in items]
        return self.items

    def itemToFeedEntry(self, item):
        bugtask = item
        bug = bugtask.bug
        title = FeedTypedData('[%s] %s' % (bug.id, bug.title))
        url = canonical_url(bugtask, rootsite="bugs")
        content_view = BugFeedContentView(bug, self.request, self.verbose)
        entry = FeedEntry(title = title,
                          id_ = url,
                          link_alternate = url,
                          date_updated = bug.date_last_updated,
                          date_published = bugtask.datecreated,
                          authors = [FeedPerson(bug.owner)],
                          content = FeedTypedData(content_view.render(),
                                                  content_type="xhtml"))
        return entry


class ProjectProductBugsFeed(BugsFeedBase):
    """Bug feeds for projects and products."""

    feed_name = "latest-bugs.atom"

    def getTitle(self):
        """Title for the feed."""
        return "Bugs in %s" % self.context.displayname

    def getRawItems(self, quantity):
        """Get the raw set of items for the feed."""
        return self.context.getLatestBugTasks(quantity=quantity)


class PersonBugsFeed(BugsFeedBase):
    """Bug feeds for a person."""

    # see PersonRelatedBugsView
    # XXX, bac: this class is currently broken

    feed_name = "latest-bugs.atom"

    def getTitle(self):
        """Title for the feed."""
        return "Bugs for %s" % self.context.displayname

    def getRawItems(self, quantity=5):
        """Get the raw set of items for the feed."""
        return self.search(quantity)


class SearchBugs(BugsFeedBase):
    """Bug feeds for a generic search.

    Searches are of the form produced by an advanced bug search, e.g.
    http://bugs.launchpad.dev/bugs/search-bugs.atom?field.searchtext=&
        search=Search+Bug+Reports&field.scope=all&field.scope.target=
    """

    feed_name = "search-bugs.atom"

    def initialize(self):
        self.task_search_listing_view = BugsBugTaskSearchListingView(self.context, self.request)
        self.task_search_listing_view.initialize()

    def getRawItems(self, quantity):
        """Perform the search."""

        results =  self.task_search_listing_view.search(searchtext=None, context=None, extra_params=None)
        items = results.getBugListingItems()
        return items[:quantity]

    def getTitle(self):
        """Title for the feed."""
        return "Bugs from custom search."
