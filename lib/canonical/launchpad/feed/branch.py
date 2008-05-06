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
from zope.component import getUtility
from zope.interface import implements
from zope.security.interfaces import Unauthorized

from canonical.launchpad.browser import (
    BranchView, PersonBranchesView, ProductBranchesView, ProjectBranchesView)
from canonical.config import config
from canonical.launchpad.webapp import canonical_url, urlappend, urlparse
from canonical.launchpad.interfaces import (
    BranchListingSort, DEFAULT_BRANCH_STATUS_IN_LISTING, IBranch, IBranchSet,
    IPerson, IProduct, IProject)
from canonical.lazr.feed import (
    FeedBase, FeedEntry, FeedPerson, FeedTypedData, MINUTES)
from canonical.lazr.interfaces import (
    IFeedPerson)


class BranchFeedEntry(FeedEntry):
    """See `IFeedEntry`."""
    def construct_id(self):
        url_path = urlparse(self.link_alternate)[2]
        return 'tag:launchpad.net,%s:/code%s' % (
            self.date_created.date().isoformat(),
            url_path)


class BranchFeedContentView(BranchView):
    """View for branch feed contents."""

    def __init__(self, context, request, feed,
                 template='templates/branch.pt'):
        super(BranchFeedContentView, self).__init__(context, request)
        self.feed = feed
        self.template_ = template
    def render(self):
        """Render the view."""
        return ViewPageTemplateFile(self.template_)(self)


class BranchFeedBase(FeedBase):
    """Abstract class for branch feeds."""

    # max_age is in seconds
    max_age = config.launchpad.max_branch_feed_cache_minutes * MINUTES

    rootsite = "code"

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

    def _getItemsWorker(self):
        """Create the list of items.

        Called by getItems which may cache the results.
        """
        items = self.getPublicRawItems()
        # Convert the items into their feed entry representation.
        items = [self.itemToFeedEntry(item) for item in items]
        return items

    def itemToFeedEntry(self, branch):
        """See `IFeed`."""
        title = FeedTypedData(branch.displayname)
        url = canonical_url(branch, rootsite=self.rootsite)
        content_view = BranchFeedContentView(branch, self.request, self)
        content = content_view.render()
        content_data = FeedTypedData(content=content,
                                     content_type="html",
                                     root_url=self.root_url)
        entry = BranchFeedEntry(title=title,
                                link_alternate=url,
                                date_created=branch.date_created,
                                date_updated=branch.date_last_modified,
                                date_published=branch.date_created,
                                # XXX if author and owner are different
                                # perhaps we should use them both?
                                authors=[FeedPerson(branch.owner,
                                                    self.rootsite)],
                                content=content_data)
        return entry


class BranchListingFeed(BranchFeedBase):
    """Feed for all branches on a product or project."""

    feedname = "branches"

    @property
    def title(self):
        """See `IFeed`."""
        return "Branches for %s" % self.context.displayname


class ProductBranchFeed(BranchListingFeed):
    """Feed for all branches on a product."""

    usedfor = IProduct

    def _getRawItems(self):
        """See `BranchFeedBase._getRawItems`.

        Return the branches for this product sorted by date_created in
        descending order.
        """
        branch_query = getUtility(IBranchSet).getBranchesForProduct(
            product=self.context, visible_by_user=None,
            lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING,
            sort_by=BranchListingSort.MOST_RECENTLY_CHANGED_FIRST)
        return list(branch_query[:self.quantity])


class ProjectBranchFeed(BranchListingFeed):
    """Feed for all branches on a product."""

    usedfor = IProject

    def _getRawItems(self):
        """See `BranchFeedBase._getRawItems`.

        Return the branches for this project sorted by date_created in
        descending order.
        """
        branch_query = getUtility(IBranchSet).getBranchesForProject(
            project=self.context, visible_by_user=None,
            lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING,
            sort_by=BranchListingSort.MOST_RECENTLY_CHANGED_FIRST)
        return list(branch_query[:self.quantity])


class PersonBranchFeed(BranchListingFeed):
    """Feed for a person's branches."""

    usedfor = IPerson

    def _getRawItems(self):
        """See `BranchFeedBase._getRawItems`.
        
        Return the branchs for this person sorted by date_created in descending
        order.
        """
        branch_query = getUtility(IBranchSet).getBranchesForPerson(
            person=self.context, visible_by_user=None,
            lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING,
            sort_by=BranchListingSort.MOST_RECENTLY_CHANGED_FIRST)
        return list(branch_query[:self.quantity])


class RevisionPerson:
    """See `IFeedPerson`.

    Uses the `name_without_email` property for the display name.
    """
    implements(IFeedPerson)

    def __init__(self, person, rootsite):

        no_email =  person.name_without_email
        if no_email:
            self.name = no_email
        else:
            self.name = person.name
        # We don't want to disclose email addresses in public feeds.
        self.email = None
        self.uri = None

class BranchFeed(BranchFeedBase):
    """Feed for single branch.

    Unlike the other branch feeds, where the feed entries were the various
    branches for that object, the feed for a single branch has as entries the
    latest revisions for that branch.
    """

    usedfor = IBranch
    feedname = "branch"
    delegate_view_class = BranchView

    def initialize(self):
        """See `IFeed`."""
        # For a `BranchFeed` we must ensure that the branch is not private.
        super(BranchFeed, self).initialize()
        if self.context.private:
            raise Unauthorized("Feeds do not serve private branches")

    @property
    def title(self):
        """See `IFeed`."""
        return "Latest Revisions for Branch %s" % self.context.displayname

    def _getRawItems(self):
        """Get the raw set of items for the feed.

        For a `BranchFeed` the items are the revisions for the branch.
        """
        branch = self.context
        return branch.latest_revisions(quantity=self.quantity)

    def _getItemsWorker(self):
        """Create the list of items.

        Called by getItems which may cache the results.
        """
        items = self._getRawItems()
        # Convert the items into their feed entry representation.
        items = [self.itemToFeedEntry(item) for item in items]
        return items

    def itemToFeedEntry(self, rev):
        """See `IFeed`."""
        delegate_view = self.delegate_view_class(self.context, self.request)
        delegate_view.initialize()
        title = FeedTypedData("Revision %d" % rev.sequence)
        url = urlappend(delegate_view.codebrowse_url,
                        "revision/%d" % rev.sequence)
        content_view = BranchFeedContentView(rev, self.request, self,
                                             'templates/branch-revision.pt')
        content = FeedTypedData(content=content_view.render(),
                                content_type="html",
                                root_url=self.root_url)
        entry = BranchFeedEntry(
            title=title,
            link_alternate=url,
            date_created=rev.revision.date_created,
            date_updated=rev.revision.revision_date,
            date_published=None,
            authors=[RevisionPerson(
                    rev.revision.revision_author,
                    self.rootsite)],
            content=content)
        return entry
