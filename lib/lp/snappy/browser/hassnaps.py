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
from lp.services.features import getFeatureFlag
from lp.services.propertycache import cachedproperty
from lp.services.webapp import Link
from lp.snappy.interfaces.snap import (
    ISnapSet,
    SNAP_FEATURE_FLAG,
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
        # You can't yet create a snap for a private branch.
        enabled = (
            bool(getFeatureFlag(SNAP_FEATURE_FLAG)) and
            not self.context.private)
        text = 'Create snap package'
        return Link('+new-snap', text, enabled=enabled, icon='add')


class HasSnapsViewMixin:
    """A view mixin for objects that implement IHasSnaps."""

    @cachedproperty
    def snap_count(self):
        context = self.context
        if isinstance(context, DecoratedBranch):
            context = context.branch
        return getUtility(ISnapSet).findByContext(
            context, visible_by_user=self.user).count()

    @property
    def show_snap_information(self):
        return bool(getFeatureFlag(SNAP_FEATURE_FLAG)) or self.snap_count != 0

    @property
    def snap_count_text(self):
        count = self.snap_count
        if count == 0:
            return 'No snap packages'
        elif count == 1:
            return '1 snap package'
        else:
            return '%s snap packages' % count
