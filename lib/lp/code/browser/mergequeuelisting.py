# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Base class view for merge queue listings."""

__metaclass__ = type

__all__ = [
    'MergeQueueListingView',
    'HasMergeQueuesMenuMixin',
    'PersonMergeQueueListingView',
    'ProductMergeQueueListingView',
    ]


from canonical.launchpad.browser.feeds import FeedsMixin
from canonical.launchpad.webapp import (
    LaunchpadView,
    Link,
    )


class HasMergeQueuesMenuMixin:
    """A context menus mixin for objects that implement IHasMergeQueues."""

    def view_merge_queues(self):
        text = 'View merge queues'
        enabled = self.context.getMergeQueues().count() > 0
#        enabled = True
        return Link(
            '+merge-queues', text, icon='info', enabled=enabled, site='code')


class MergeQueueListingView(LaunchpadView, FeedsMixin):

    feed_types = ()

    branch_enabled = True
    owner_enabled = True

    @property
    def page_title(self):
        return 'Merge Queues for %(displayname)s' % {
            'displayname': self.context.displayname}


class PersonMergeQueueListingView(MergeQueueListingView):

    owner_enabled = False

