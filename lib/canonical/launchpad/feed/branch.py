# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Branch feed (syndication) views."""

__metaclass__ = type

__all__ = [
    'BranchFeed',
    ]

from zope.security.interfaces import Unauthorized

from canonical.config import config
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.interfaces import IBranch
from canonical.lazr.feed import (
    FeedBase, FeedEntry, FeedPerson, FeedTypedData, MINUTES)


class BranchFeedContentView(LaunchpadView):
    """View for a branch feed contents."""

    def __init__(self, context, request, feed):
        super(BranchFeedContentView, self).__init__(context, request)
        self.feed = feed

    @property
    def branch_for_display(self):
        """Get the rendered branch revisions.

        Using the existing templates and views, transform the information for
        the branch into a representation to be used as the 'content' in the
        branch feed.
        """
        branch_task_view = BugTaskView(self.context.bugtasks[0], self.request)
        return bug_task_view.getBugCommentsForDisplay()

    def render(self):
        """Render the view."""
        return ViewPageTemplateFile('templates/branch.pt')(self)


class BranchFeedBase(FeedBase):
    """Abstract class for branch feeds."""

    # max_age is in seconds
    max_age = config.launchpad.max_branch_feed_cache_minutes * MINUTES

    rootsite = "code"

    def initialize(self):
        """See `IFeed`."""
        super(BranchFeedBase, self).initialize()
        self.setupColumns()

    def setupColumns(self):
        """Set up the columns to be displayed in the feed.

        This method may need to be overridden to customize the display for
        different feeds.
        """
        self.show_column = dict(
            id = True,
            title = True,
            summary = True,
            owner = True,
            author = True,
            unique_name = True,
            )

    @property
    def url(self):
        """See `IFeed`."""
        return "%s/%s.%s" % (
            canonical_url(self.context), self.feedname, self.format)

    @property
    def logo(self):
        """See `IFeed`."""
        return "%s/@@/branch" % self.site_url

    def _getRawItems(self):
        """Get the raw set of items for the feed."""
        raise NotImplementedError

    def getPublicRawItems(self):
        """Private branchess are not to be shown in feeds.

        The list of branches is screened to ensure no private branches are
        returned.
        """
        return [branch
                for branch in self._getRawItems()
                if not branch.private]

    def getItems(self):
        """See `IFeed`."""
        items = self.getPublicRawItems()
        # Convert the items into their feed entry representation.
        items = [self.itemToFeedEntry(item) for item in items]
        return items

    def itemToFeedEntry(self, branch):
        """See `IFeed`."""
        title = FeedTypedData('[%s] %s' % (branch.id, branch.title))
        url = canonical_url(branch, rootsite=self.rootsite)
        #content_view = BranchFeedContentView(branch, self.request, self)
        entry = FeedEntry(title=title,
                          id_=url,
                          link_alternate=url,
                          date_updated=branch.date_last_modified,
                          date_published=branch.date_created,
                          # XXX
                          # if author and owner are different perhaps we
                          # should use them both?
                          authors=[FeedPerson(branch.owner, self.rootsite)],
                          content=branch.summary)
        return entry


class BranchFeed(BranchFeedBase):
    """Feed for single branch."""

    usedfor = IBranch
    feedname = "branch"

    def initialize(self):
        """See `IFeed`."""
        # For a `BranchFeed` we must ensure that the branch is not private.
        super(BranchFeed, self).initialize()
        if self.context.private:
            raise Unauthorized("Feeds do not serve private branches")

    @property
    def title(self):
        """See `IFeed`."""
        return "Branch %s" % self.context.id

    def _getRawItems(self):
        """Get the raw set of items for the feed."""
        return [self.context]
