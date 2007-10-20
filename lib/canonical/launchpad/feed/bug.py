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
from zope.security.interfaces import Unauthorized

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.publisher import LaunchpadView
from canonical.launchpad.browser.bugtask import BugTaskView
from canonical.launchpad.browser import (
    BugsBugTaskSearchListingView, BugTargetView,
    PersonRelatedBugsView)
from canonical.launchpad.interfaces import (
    IBug, IBugTarget, IBugTaskSet, IMaloneApplication, IPerson)
from canonical.lazr.feed import (
    FeedBase, FeedEntry, FeedPerson, FeedTypedData, MINUTES)
from canonical.lazr.interfaces import IFeed

# XXX - bac 2-Oct-2007 - Bug 153785 - this value should be in a config file.
BUG_MAX_AGE = 30 * MINUTES


def get_unique_bug_tasks(items):
    """Given a list of BugTasks return a list with one BugTask per Bug.

    A Bug can have many BugTasks.  In order to avoid duplicate data, the list
    is trimmed to have only one representative BugTask per Bug.
    """
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
        self.feed = feed

    @property
    def bug_comments_for_display(self):
        """Get the rendered bug comments.

        Using the existing templates and views, transform the comments for the
        bug into a representation to be used as the 'content' in the bug feed.
        """
        bug_task_view = BugTaskView(self.context.bugtasks[0], self.request)
        return bug_task_view.getBugCommentsForDisplay()

    def render(self):
        """Render the view."""
        return ViewPageTemplateFile('templates/bug.pt')(self)


class BugsFeedBase(FeedBase):
    """Abstract class for bug feeds."""

    max_age = BUG_MAX_AGE
    rootsite = "bugs"
    show_column = dict(
        id = True,
        title = True,
        bugtargetdisplayname = True,
        importance = True,
        status = True)

    @property
    def url(self):
        """See `IFeed`."""
        return "%s/%s.%s" % (
            canonical_url(self.context), self.feedname, self.format)

    @property
    def logo(self):
        """See `IFeed`."""
        return "%s/@@/bug" % self.site_url

    def _getRawItems(self):
        """Get the raw set of items for the feed."""
        raise NotImplementedError

    def getPublicRawItems(self):
        """Private bugs are not to be shown in feeds.

        The list of bugs is screened to ensure no private bugs are returned.
        """
        return [bugtask
                for bugtask in self._getRawItems()
                if not bugtask.bug.private]

    def getItems(self):
        """See `IFeed`."""
        items = self.getPublicRawItems()
        # Convert the items into their feed entry representation.
        items = [self.itemToFeedEntry(item) for item in items]
        return items

    def itemToFeedEntry(self, bugtask):
        """See `IFeed`."""
        bug = bugtask.bug
        title = FeedTypedData('[%s] %s' % (bug.id, bug.title))
        url = canonical_url(bugtask, rootsite=self.rootsite)
        content_view = BugFeedContentView(bug, self.request, self)
        entry = FeedEntry(title=title,
                          id_=url,
                          link_alternate=url,
                          date_updated=bug.date_last_updated,
                          date_published=bugtask.datecreated,
                          authors=[FeedPerson(bug.owner, self.rootsite)],
                          content=FeedTypedData(content_view.render(),
                                                content_type="xhtml"))
        return entry

    def renderHTML(self):
        """See `IFeed`."""
        return ViewPageTemplateFile('templates/bug-html.pt')(self)


class BugFeed(BugsFeedBase):
    """Bug feeds for single bug."""

    usedfor = IBug
    feedname = "bug"

    def initialize(self):
        """See `IFeed`."""
        # For a `BugFeed` we must ensure that the bug is not private.
        super(BugFeed, self).initialize()
        if self.context.private:
            raise Unauthorized("Feeds do not serve private bugs")

    @property
    def title(self):
        """See `IFeed`."""
        return "Bug %s" % self.context.id

    def _getRawItems(self):
        """Get the raw set of items for the feed."""
        bugtasks = list(self.context.bugtasks)
        # All of the bug tasks are for the same bug.
        return bugtasks[:1]


class BugTargetBugsFeed(BugsFeedBase):
    """Bug feeds for projects and products."""

    usedfor = IBugTarget
    feedname = "latest-bugs"
    # Make a copy of the inherited class variable so the one copy does get
    # mutated for all subclasses.
    show_column = BugsFeedBase.show_column.copy()
    del show_column['bugtargetdisplayname']

    @property
    def title(self):
        """See `IFeed`."""
        return "Bugs in %s" % self.context.displayname

    def _getRawItems(self):
        """Get the raw set of items for the feed."""
        delegate_view = BugTargetView(self.context, self.request)
        delegate_view.initialize()
        return delegate_view.latestBugTasks(quantity=self.quantity)


class PersonBugsFeed(BugsFeedBase):
    """Bug feeds for a person."""

    usedfor = IPerson
    feedname = "latest-bugs"

    @property
    def title(self):
        """See `IFeed`."""
        return "Bugs for %s" % self.context.displayname

    def _getRawItems(self):
        """Perform the search."""
        delegate_view = PersonRelatedBugsView(self.context, self.request)
        delegate_view.initialize()
        results = delegate_view.search()
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

    def _getRawItems(self):
        """Perform the search."""
        search_context = getUtility(IMaloneApplication)
        delegate_view = BugsBugTaskSearchListingView(self.context,
                                                     self.request)
        delegate_view.initialize()
        results = delegate_view.search(searchtext=None,
                      context=search_context, extra_params=None)
        items = results.getBugListingItems()
        return get_unique_bug_tasks(items)[:self.quantity]

    @property
    def title(self):
        """See `IFeed`."""
        return "Bugs from custom search"

    @property
    def url(self):
        """See `IFeed`."""
        return "%s?%s" % (self.request.getURL(),
                          self.request.get('QUERY_STRING'))
