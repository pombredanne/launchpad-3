# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BugSubscriptionFilter']

from storm.base import Storm
from storm.locals import (
    Bool,
    Int,
    Reference,
    Unicode,
    )

from canonical.launchpad.interfaces.lpstorm import IStore
from lp.bugs.model.bugsubscriptionfilterimportance import (
    BugSubscriptionFilterImportance,
    )
from lp.bugs.model.bugsubscriptionfilterstatus import (
    BugSubscriptionFilterStatus,
    )
from lp.bugs.model.bugsubscriptionfiltertag import (
    BugSubscriptionFilterTag,
    )


class BugSubscriptionFilter(Storm):
    """A filter to specialize a *structural* subscription."""

    __storm_table__ = "BugSubscriptionFilter"

    id = Int(primary=True)

    structural_subscription_id = Int(
        "structuralsubscription", allow_none=False)
    structural_subscription = Reference(
        structural_subscription_id, "StructuralSubscription.id")

    find_all_tags = Bool(allow_none=False, default=False)
    include_any_tags = Bool(allow_none=False, default=False)
    exclude_any_tags = Bool(allow_none=False, default=False)

    other_parameters = Unicode()

    description = Unicode()

    def _get_statuses(self):
        """Return a frozenset of statuses to filter on."""
        return frozenset(
            IStore(BugSubscriptionFilterStatus).find(
                BugSubscriptionFilterStatus,
                BugSubscriptionFilterStatus.filter == self).values(
                BugSubscriptionFilterStatus.status))

    def _set_statuses(self, statuses):
        """Update the statuses to filter on.

        The statuses must be from the `BugTaskStatus` enum, but can be
        bundled in any iterable.
        """
        statuses = frozenset(statuses)
        current_statuses = self.statuses
        store = IStore(BugSubscriptionFilterStatus)
        # Add additional statuses.
        for status in statuses.difference(current_statuses):
            status_filter = BugSubscriptionFilterStatus()
            status_filter.filter = self
            status_filter.status = status
            store.add(status_filter)
        # Delete unused ones.
        store.find(
            BugSubscriptionFilterStatus,
            BugSubscriptionFilterStatus.filter == self,
            BugSubscriptionFilterStatus.status.is_in(
                current_statuses.difference(statuses))).remove()

    statuses = property(
        _get_statuses, _set_statuses, doc=(
            "A frozenset of statuses filtered on."))

    def _get_importances(self):
        """Return a frozenset of importances to filter on."""
        return frozenset(
            IStore(BugSubscriptionFilterImportance).find(
                BugSubscriptionFilterImportance,
                BugSubscriptionFilterImportance.filter == self).values(
                BugSubscriptionFilterImportance.importance))

    def _set_importances(self, importances):
        """Update the importances to filter on.

        The importances must be from the `BugTaskImportance` enum, but can be
        bundled in any iterable.
        """
        importances = frozenset(importances)
        current_importances = self.importances
        store = IStore(BugSubscriptionFilterImportance)
        # Add additional importances.
        for importance in importances.difference(current_importances):
            importance_filter = BugSubscriptionFilterImportance()
            importance_filter.filter = self
            importance_filter.importance = importance
            store.add(importance_filter)
        # Delete unused ones.
        store.find(
            BugSubscriptionFilterImportance,
            BugSubscriptionFilterImportance.filter == self,
            BugSubscriptionFilterImportance.importance.is_in(
                current_importances.difference(importances))).remove()

    importances = property(
        _get_importances, _set_importances, doc=(
            "A frozenset of importances filtered on."))

    def _get_tags(self):
        """Return a frozenset of tags to filter on."""
        tag_filters = IStore(BugSubscriptionFilterTag).find(
            BugSubscriptionFilterTag,
            BugSubscriptionFilterTag.filter == self)
        return frozenset(
            tag_filter.tag if tag_filter.include else u"-%s" % tag_filter.tag
            for tag_filter in tag_filters)

    def _set_tags(self, tags):
        """Update the tags to filter on.

        The tags must be from the `BugTaskTag` enum, but can be
        bundled in any iterable.
        """
        tags = frozenset(tags)
        current_tags = self.tags
        store = IStore(BugSubscriptionFilterTag)
        # Add additional tags.
        for tag in tags.difference(current_tags):
            tag_filter = BugSubscriptionFilterTag()
            tag_filter.filter = self
            tag_filter.include = not tag.startswith("-")
            tag_filter.tag = tag.lstrip("-")
            store.add(tag_filter)
        # Delete unused ones.
        store.find(
            BugSubscriptionFilterTag,
            BugSubscriptionFilterTag.filter == self,
            BugSubscriptionFilterTag.tag.is_in(
                current_tags.difference(tags))).remove()

    tags = property(
        _get_tags, _set_tags, doc=(
            "A frozenset of tags filtered on."))
