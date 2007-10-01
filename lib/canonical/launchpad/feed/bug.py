# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Bug feed (syndication) views."""

__metaclass__ = type

__all__ = [
    'BugTargetBugsFeed',
    'PersonBugsFeed',
    'SearchBugsFeed',
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
from canonical.launchpad.interfaces import (
    IBugTarget, IBugTaskSet, IPerson)


class BugFeedContentView(LaunchpadView):
    """View for a bug feed contents."""

    short_template = ViewPageTemplateFile('templates/bug.pt')
    long_template = ViewPageTemplateFile('templates/bug-verbose.pt')

    def __init__(self, context, request, verbose=False):
        super(BugFeedContentView, self).__init__(context, request)
        self.verbose = verbose
        self.format = None

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

    def initialize(self):
        super(BugsFeedBase, self).initialize()
        self.getParameters()

    def getParameters(self):
        verbose = self.request.get('verbose')
        if verbose is not None:
            if verbose.lower() in ['1', 't', 'true', 'yes']:
                self.verbose = True
        extension = self.request['PATH_INFO'].split('/')[-1].split('.')[-1]
        path = self.request['PATH_INFO']
        if path.endswith('.atom'):
            self.format = 'atom'
        elif path.endswith('.html'):
            self.format = 'html'
        else:
            raise ValueError, ('%s in %s is not atom or html'
                % (extension, self.request['PATH_INFO']))

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
        """Given a set of items, format them for rendering."""
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

class BugTargetBugsFeed(BugsFeedBase):
    """Bug feeds for projects and products."""

    usedfor = IBugTarget
    feed_name = "latest-bugs.atom"

    def initialize(self):
        super(BugTargetBugsFeed, self).initialize()
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

    usedfor = IPerson
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


class SearchBugsFeed(BugsFeedBase):
    """Bug feeds for a generic search.

    Searches are of the form produced by an advanced bug search, e.g.
    http://bugs.launchpad.dev/bugs/search-bugs.atom?field.searchtext=&
        search=Search+Bug+Reports&field.scope=all&field.scope.target=
    """

    usedfor = IBugTaskSet
    feed_name = "search-bugs.atom"

    def initialize(self):
        super(SearchBugsFeed, self).initialize()
        self.delegate_view = BugsBugTaskSearchListingView(self.context, self.request)
        self.delegate_view.initialize()

    def getRawItems(self):
        """Perform the search."""

        results =  self.delegate_view.search(searchtext=None, context=None, extra_params=None)
        items = results.getBugListingItems()
        return items[:self.quantity]

    def getTitle(self):
        """Title for the feed."""
        return "Bugs from custom search"

    def getURL(self):
        """Get the identifying URL for the feed."""
        return "%s?%s" % (self.request.getURL(), self.request.get('QUERY_STRING'))
