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
    LaunchpadFormView,
    Link,
    )
from lp.code.interfaces.branchmergequeuecollection import (
    IBranchMergeQueueCollection)
from lp.services.browser_helpers import get_plural_text
from lp.services.propertycache import cachedproperty


class HasMergeQueuesMenuMixin:
    """A context menus mixin for objects that implement IHasMergeQueues."""

    @property
    def person(self):
        """The `IPerson` for the context of the view.

        In simple cases this is the context itself, but in others, like the
        PersonProduct, it is an attribute of the context.
        """
        return self.context

    def mergequeues(self):
        return Link(
            '+merge-queues',
            get_plural_text(
                self.mergequeue_count(),
                'merge queue', 'merge queues'), site='code')

    def mergequeue_count(self):
        return IBranchMergeQueueCollection(
            self.person).getMergeQueues().count()


class MergeQueueListingView(LaunchpadFormView, FeedsMixin):

    feed_types = ()

    branch_enabled = True
    owner_enabled = True

    @property
    def page_title(self):
        return 'Merge Queues for %(displayname)s' % {
            'displayname': self.context.displayname}

    def getVisibleQueuesForUser(self):
        """Branch merge queuea that are visible by the logged in user."""
        merge_queues = IBranchMergeQueueCollection(self.context)
        #XXX only get queues visible to logged in user self.user
        return merge_queues.getMergeQueues()

    @cachedproperty
    def mergequeues(self):
        merge_queues = IBranchMergeQueueCollection(self.context)
        merge_queues.getMergeQueues()

    @cachedproperty
    def mergequeue_count(self):
        """Return the number of merge queues that will be returned."""
        return self.getVisibleQueuesForUser().count()

    @property
    def no_merge_queue_message(self):
        """Shown when there is no table to show."""
        return "%s has no merge proposals." % self.context.displayname


class PersonMergeQueueListingView(MergeQueueListingView):

    owner_enabled = False

