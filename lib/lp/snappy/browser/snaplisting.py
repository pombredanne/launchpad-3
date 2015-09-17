# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Base class view for snap listings."""

__metaclass__ = type

__all__ = [
    'BranchSnapListingView',
    'GitSnapListingView',
    'PersonSnapListingView',
    ]

from functools import partial

from zope.component import getUtility

from lp.code.browser.decorations import DecoratedBranch
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.feeds.browser import FeedsMixin
from lp.services.webapp import (
    canonical_url,
    LaunchpadView,
    )
from lp.snappy.interfaces.snap import ISnapSet


class SnapListingView(LaunchpadView, FeedsMixin):

    feed_types = ()

    source_enabled = True
    owner_enabled = True

    @property
    def page_title(self):
        return 'Snap packages'

    @property
    def label(self):
        return 'Snap packages for %(displayname)s' % {
            'displayname': self.context.displayname}

    def initialize(self):
        super(SnapListingView, self).initialize()
        snaps = getUtility(ISnapSet).findByContext(
            self.context, visible_by_user=self.user)
        loader = partial(
            getUtility(ISnapSet).preloadDataForSnaps, user=self.user)
        self.snaps = DecoratedResultSet(snaps, pre_iter_hook=loader)
        if self.snaps.count() == 1:
            snap = self.snaps.one()
            self.request.response.redirect(canonical_url(snap))


class BranchSnapListingView(SnapListingView):

    source_enabled = False

    def initialize(self):
        super(BranchSnapListingView, self).initialize()
        # Replace our context with a decorated branch, if it is not already
        # decorated.
        if not isinstance(self.context, DecoratedBranch):
            self.context = DecoratedBranch(self.context)


class GitSnapListingView(SnapListingView):

    source_enabled = False

    @property
    def label(self):
        return 'Snap packages for %(display_name)s' % {
            'display_name': self.context.display_name}


class PersonSnapListingView(SnapListingView):

    owner_enabled = False


class ProjectSnapListingView(SnapListingView):
    pass
