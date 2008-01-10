# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Branch feed (syndication) views."""

__metaclass__ = type

__all__ = [
    'BranchFeed',
    'PersonBranchFeed',
    'ProductBranchFeed',
    'ProjectBranchFeed',
    ]

from zope.app.pagetemplate import ViewPageTemplateFile
from zope.security.interfaces import Unauthorized

from canonical.launchpad.browser import (
    BranchView, PersonBranchesView, ProductBranchesView, ProjectBranchesView)
from canonical.config import config
from canonical.launchpad.webapp import canonical_url, urlparse
from canonical.launchpad.interfaces import (
    IBranch, IPerson, IProduct, IProject)
from canonical.lazr.feed import (
    FeedBase, FeedEntry, FeedPerson, FeedTypedData, MINUTES)


class BranchFeedEntry(FeedEntry):
    """See `IFeedEntry`."""
    def construct_id(self):
        url_path = urlparse(self.link_alternate)[2]
        return 'tag:launchpad.net,%s:/code%s' % (
            self.date_created.date().isoformat(),
            url_path)


class BranchFeedContentView(BranchView):
    """View for branch feed contents."""

    def __init__(self, context, request, feed):
        super(BranchFeedContentView, self).__init__(context, request)
        self.feed = feed

    def render(self):
        """Render the view."""
        return ViewPageTemplateFile('templates/branch.pt')(self)


class BranchFeedBase(FeedBase):
    """Abstract class for branch feeds."""

    # max_age is in seconds
    max_age = config.launchpad.max_branch_feed_cache_minutes * MINUTES

    rootsite = "code"

    @property
    def link_self(self):
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
        title = FeedTypedData(branch.displayname)
        url = canonical_url(branch, rootsite=self.rootsite)
        content_view = BranchFeedContentView(branch, self.request, self)
        content = FeedTypedData(content=content_view.render(),
                                content_type="xhtml")
        entry = BranchFeedEntry(title=title,
                                link_alternate=url,
                                date_created=branch.date_created,
                                date_updated=branch.date_last_modified,
                                date_published=branch.date_created,
                                # XXX if author and owner are different
                                # perhaps we should use them both?
                                authors=[FeedPerson(branch.owner,
                                                    self.rootsite)],
                                content=content)
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
        return "Branch %s" % self.context.displayname

    def _getRawItems(self):
        """Get the raw set of items for the feed."""
        return [self.context]


class BranchListingFeed(BranchFeedBase):
    """Feed for all branches on a product or project."""

    feedname = "branches"

    def initialize(self):
        """See `IFeed`."""
        super(BranchListingFeed, self).initialize()

    @property
    def title(self):
        """See `IFeed`."""
        return "Branches for %s" % self.context.displayname

    def _getRawItems(self):
        """Get the raw set of items for the feed."""
        delegate_view = self.delegate_view_class(self.context, self.request)
        delegate_view.initialize()
        branches_batch = delegate_view.branches()
        batch_list = branches_batch.getBatches()
        # Assuming the branches are unique.
        branches = []
        for batch in batch_list:
            branches.extend(list(batch.list))
            if len(branches) >= self.quantity:
                break
        return branches[:self.quantity]


class ProductBranchFeed(BranchListingFeed):
    """Feed for all branches on a product."""

    usedfor = IProduct
    delegate_view_class = ProductBranchesView

    def initialize(self):
        """See `IFeed`."""
        super(ProductBranchFeed, self).initialize()


class ProjectBranchFeed(BranchListingFeed):
    """Feed for all branches on a product."""

    usedfor = IProject
    delegate_view_class = ProjectBranchesView

    def initialize(self):
        """See `IFeed`."""
        super(ProjectBranchFeed, self).initialize()


class PersonBranchFeed(BranchListingFeed):
    """Feed for a person's branches."""

    usedfor = IPerson
    delegate_view_class = PersonBranchesView

    def initialize(self):
        """See `IFeed`."""
        super(PersonBranchFeed, self).initialize()
