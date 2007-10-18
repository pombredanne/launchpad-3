# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Bug feed (syndication) views."""

__metaclass__ = type

__all__ = [
    'BugFeed',
    'BugTargetBugsFeed',
    'PersonBugsFeed',
    'SearchBugsFeed',
    ]

from zope.app.pagetemplate import ViewPageTemplateFile
from zope.component import getUtility
from canonical.lazr.feed import (
    FeedBase, FeedEntry, FeedPerson, FeedTypedData, MINUTES)
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.publisher import LaunchpadView
from canonical.launchpad.browser.bugtask import BugTaskView
from canonical.launchpad.browser import (
    BugsBugTaskSearchListingView, BugTargetView,
    PersonRelatedBugsView)
from canonical.launchpad.interfaces import (
    IBug,
    IBugTarget,
    IBugTaskSet,
    IMaloneApplication,
    IPerson,
    )


def get_unique_bug_tasks(items):
    ids = set()
    unique_items = []
    for item in items:
        if item.bug.id in ids:
            continue
        ids.add(item.bug.id)
        unique_items.append(item)
    return unique_items


class BugFeedContentView(LaunchpadView):
    """View for a bug feed contents."""

    def __init__(self, context, request, feed):
        super(BugFeedContentView, self).__init__(context, request)
        self.format = None
        self.feed = feed

    def getBugCommentsForDisplay(self):
        bug_task_view = BugTaskView(self.context.bugtasks[0], self.request)
        return bug_task_view.getBugCommentsForDisplay()

    def render(self):
        return ViewPageTemplateFile('templates/bug.pt')(self)


class BugsFeedBase(FeedBase):
    """Abstract class for bug feeds."""

    max_age = 30 * MINUTES
    rootsite = "bugs"

    def initialize(self):
        super(BugsFeedBase, self).initialize()
        self.__show_column = None

    @property
    def show_column(self):
        if self.__show_column is not None:
            return self.__show_column
        self.__show_column = dict(
            id = True,
            title = True,
            bugtargetdisplayname = True,
            importance = True,
            status = True)
        if IBugTarget.providedBy(self.context):
            self.__show_column['bugtargetdisplayname'] = False
        override = self.request.get('show_column')
        if override:
            for column in override.split(','):
                if len(column) == 0:
                    continue
                elif column[0] == '-':
                    value = False
                    column = column[1:]
                    if len(column) == 0:
                        continue
                else:
                    value = True
                self.__show_column[column] = value
        return self.__show_column

    def getURL(self):
        """Get the identifying URL for the feed."""
        return "%s/%s.%s" % (
          canonical_url(self.context), self.feedname, self.format)

    def getLogo(self):
        """Get the application-specific logo."""
        return "%s/@@/bug" % self.getSiteURL()

    def getPublicRawItems(self):
        return [ bugtask
                 for bugtask in self.getRawItems()
                 if not bugtask.bug.private ]

    def getItems(self):
        """Get the items for the feed.

        The result is assigned to self.items for caching.
        """
        if self.items is None:
            items = self.getPublicRawItems()
            self.items = [self.itemToFeedEntry(item) for item in items]
        return self.items

    def itemToFeedEntry(self, item):
        """Given a set of items, format them for rendering."""
        bugtask = item
        bug = bugtask.bug
        title = FeedTypedData('[%s] %s' % (bug.id, bug.title))
        url = canonical_url(bugtask, rootsite=self.rootsite)
        content_view = BugFeedContentView(bug, self.request, self)
        entry = FeedEntry(title = title,
                          id_ = url,
                          link_alternate = url,
                          date_updated = bug.date_last_updated,
                          date_published = bugtask.datecreated,
                          authors = [FeedPerson(bug.owner, self.rootsite)],
                          content = FeedTypedData(content_view.render(),
                                                  content_type="xhtml"))
        return entry

    def renderHTML(self):
        return ViewPageTemplateFile('templates/bug-html.pt')(self)


class BugFeed(BugsFeedBase):
    """Bug feeds for single bug."""

    usedfor = IBug
    feedname = "bug"

    def initialize(self):
        super(BugFeed, self).initialize()

    def getTitle(self):
        """Title for the feed."""
        return "Bug %s" % self.context.id

    def getRawItems(self):
        """Get the raw set of items for the feed."""
        bugtasks = list(self.context.bugtasks)
        # All of the bug tasks are for the same bug
        return bugtasks[:1]


class BugTargetBugsFeed(BugsFeedBase):
    """Bug feeds for projects and products."""

    usedfor = IBugTarget
    feedname = "latest-bugs"

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
    feedname = "latest-bugs"

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
        return get_unique_bug_tasks(items)[:self.quantity]


class SearchBugsFeed(BugsFeedBase):
    """Bug feeds for a generic search.

    Searches are of the form produced by an advanced bug search, e.g.
    http://bugs.launchpad.dev/bugs/+bugs.atom?field.searchtext=&
        search=Search+Bug+Reports&field.scope=all&field.scope.target=
    """

    usedfor = IBugTaskSet
    feedname = "+bugs"

    def initialize(self):
        super(SearchBugsFeed, self).initialize()
        self.delegate_view = BugsBugTaskSearchListingView(self.context, self.request)
        self.delegate_view.initialize()

    def getRawItems(self):
        """Perform the search."""

        search_context = getUtility(IMaloneApplication)
        results =  self.delegate_view.search(searchtext=None,
            context=search_context, extra_params=None)
        items = results.getBugListingItems()
        return get_unique_bug_tasks(items)[:self.quantity]

    def getTitle(self):
        """Title for the feed."""
        return "Bugs from custom search"

    def getURL(self):
        """Get the identifying URL for the feed."""
        return "%s?%s" % (self.request.getURL(), self.request.get('QUERY_STRING'))
