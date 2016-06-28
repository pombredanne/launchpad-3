# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Mixins for browser classes for objects that implement IHasSnaps."""

__metaclass__ = type
__all__ = [
    'HasSnapsMenuMixin',
    'HasSnapsViewMixin',
    ]

from zope.component import getUtility

from lp.code.browser.decorations import DecoratedBranch
from lp.code.interfaces.gitrepository import IGitRepository
from lp.services.features import getFeatureFlag
from lp.services.webapp import (
    canonical_url,
    Link,
    )
from lp.services.webapp.escaping import structured
from lp.snappy.interfaces.snap import (
    ISnapSet,
    SNAP_PRIVATE_FEATURE_FLAG,
    )


class HasSnapsMenuMixin:
    """A mixin for context menus for objects that implement IHasSnaps."""

    def view_snaps(self):
        text = 'View snap packages'
        context = self.context
        if isinstance(context, DecoratedBranch):
            context = context.branch
        enabled = not getUtility(ISnapSet).findByContext(
            context, visible_by_user=self.user).is_empty()
        return Link('+snaps', text, icon='info', enabled=enabled)

    def create_snap(self):
        # Only enabled if the general snap feature flag is enabled
        # for public contexts and additionally if the snap_private
        # flag is enabled for private contexts.
        enabled = (
            not self.context.private or
            bool(getFeatureFlag(SNAP_PRIVATE_FEATURE_FLAG)))

        text = 'Create snap package'
        return Link('+new-snap', text, enabled=enabled, icon='add')


class HasSnapsViewMixin:
    """A view mixin for objects that implement IHasSnaps."""

    @property
    def snaps(self):
        context = self.context
        if isinstance(context, DecoratedBranch):
            context = context.branch
        return getUtility(ISnapSet).findByContext(
            context, visible_by_user=self.user)

    @property
    def show_snap_information(self):
        return not self.snaps.is_empty()

    @property
    def snaps_link(self):
        """A link to snap packages for this object."""
        count = self.snaps.count()
        if IGitRepository.providedBy(self.context):
            context_type = 'repository'
        else:
            context_type = 'branch'
        if count == 0:
            # Nothing to link to.
            return 'No snap packages using this %s.' % context_type
        elif count == 1:
            # Link to the single snap package.
            return structured(
                '<a href="%s">1 snap package</a> using this %s.',
                canonical_url(self.snaps.one()), context_type).escapedtext
        else:
            # Link to a snap package listing.
            return structured(
                '<a href="+snaps">%s snap packages</a> using this %s.',
                count, context_type).escapedtext
