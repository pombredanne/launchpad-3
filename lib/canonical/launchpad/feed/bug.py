# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Bug feed (syndication) views."""

__metaclass__ = type

__all__ = [
    'PersonBugsFeed',
    'ProjectProductBugsFeed',
    'SearchBugs',
    ]

from zope.app.pagetemplate import ViewPageTemplateFile

from canonical.lazr.feed import (
    FeedBase, FeedEntry, FeedPerson, FeedTypedData, MINUTES)
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.publisher import LaunchpadView
from canonical.launchpad.browser.bugtask import BugTaskView
from canonical.launchpad.browser import (
    BugsBugTaskSearchListingView, BugTargetView,
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
    quantity = 15
    def initialize(self):
        super(BugsFeedBase, self).initialize()
        self.getParameters()

    def getParameters(self):
        verbose = self.request.get('verbose')
        if verbose is not None:
            if verbose.lower() in ['1', 't', 'true', 'yes']:
                self.verbose = True
        quantity = self.request.get('quantity')
        if quantity is not None:
            try:
                self.quantity = int(quantity)
            except ValueError:
                pass

    def getURL(self):
        """Get the identifying URL for the feed."""
        return "%s/%s" % (canonical_url(self.context), self.feed_name)

    def getLogo(self):
        return "http://launchpad.dev/+icing/app-bugs.gif"

    def getItems(self):
        """Get the items for the feed.

        The result is assigned to self.items for caching.
        """
        if self.items is None:
            items = self.getRawItems()
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

    def initialize(self):
        super(ProjectProductBugsFeed, self).initialize()
        self.delegate_view = BugTargetView(self.context, self.request)
        self.delegate_view.initialize()

    def getTitle(self):
        """Title for the feed."""
        return "Bugs in %s" % self.context.displayname

    def getRawItems(self):
        """Get the raw set of items for the feed."""
        return self.delegate_view.latestBugTasks(quantity=self.quantity)


class PersonBugsFeed(BugsFeedBase):
    """Bug feeds for a person."""

    # see PersonRelatedBugsView
    # XXX, bac: this class is currently broken

    feed_name = "latest-bugs.atom"

    def initialize(self):
        super(PersonBugsFeed, self).initialize()
        self.delegate_view = PersonRelatedBugsView(self.context, self.request)
        self.delegate_view.initialize()

    def getTitle(self):
        """Title for the feed."""
        return "Bugs for %s" % self.context.displayname

    def getRawItems(self):
        """Perform the search."""

        results =  self.delegate_view.search()
        items = results.getBugListingItems()
        return items[:self.quantity]


class SearchBugs(BugsFeedBase):
    """Bug feeds for a generic search.

    Searches are of the form produced by an advanced bug search, e.g.
    http://bugs.launchpad.dev/bugs/search-bugs.atom?field.searchtext=&
        search=Search+Bug+Reports&field.scope=all&field.scope.target=
    """

    feed_name = "search-bugs.atom"

    def initialize(self):
        super(SearchBugs, self).initialize()
        self.delegate_view = BugsBugTaskSearchListingView(self.context, self.request)
        self.delegate_view.initialize()

    def getRawItems(self):
        """Perform the search."""

        results =  self.delegate_view.search(searchtext=None, context=None, extra_params=None)
        items = results.getBugListingItems()
        return items[:self.quantity]

    def getTitle(self):
        """Title for the feed."""
        return "Bugs from custom search."
