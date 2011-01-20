# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BugSubscriptionFilter']

from itertools import chain

from storm.locals import (
    Bool,
    Int,
    Reference,
    Store,
    Unicode,
    )
from zope.interface import implements

from canonical.launchpad import searchbuilder
from canonical.launchpad.interfaces.lpstorm import IStore
from lp.bugs.interfaces.bugsubscriptionfilter import IBugSubscriptionFilter
from lp.bugs.model.bugsubscriptionfilterimportance import (
    BugSubscriptionFilterImportance,
    )
from lp.bugs.model.bugsubscriptionfilterstatus import (
    BugSubscriptionFilterStatus,
    )
from lp.bugs.model.bugsubscriptionfiltertag import BugSubscriptionFilterTag
from lp.services.database.stormbase import StormBase


class BugSubscriptionFilter(StormBase):
    """A filter to specialize a *structural* subscription."""

    implements(IBugSubscriptionFilter)

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
        wildcards = []
        if self.include_any_tags:
            wildcards.append(u"*")
        if self.exclude_any_tags:
            wildcards.append(u"-*")
        tags = (
            tag_filter.qualified_tag
            for tag_filter in IStore(BugSubscriptionFilterTag).find(
                BugSubscriptionFilterTag,
                BugSubscriptionFilterTag.filter == self))
        return frozenset(chain(wildcards, tags))

    def _set_tags(self, tags):
        """Update the tags to filter on.

        The tags can be qualified with a leading hyphen, and can be bundled in
        any iterable.

        If they are passed within a `searchbuilder.any` or `searchbuilder.all`
        object, the `find_all_tags` attribute will be updated to match.

        Wildcard tags - `*` and `-*` - can be given too, and will update
        `include_any_tags` and `exclude_any_tags`.
        """
        # Deal with searchbuilder terms.
        if isinstance(tags, searchbuilder.all):
            self.find_all_tags = True
            tags = frozenset(tags.query_values)
        elif isinstance(tags, searchbuilder.any):
            self.find_all_tags = False
            tags = frozenset(tags.query_values)
        else:
            # Leave find_all_tags unchanged.
            tags = frozenset(tags)
        wildcards = frozenset((u"*", u"-*")).intersection(tags)
        # Set wildcards.
        self.include_any_tags = "*" in wildcards
        self.exclude_any_tags = "-*" in wildcards
        # Deal with other tags.
        tags = tags - wildcards
        store = IStore(BugSubscriptionFilterTag)
        current_tag_filters = dict(
            (tag_filter.qualified_tag, tag_filter)
            for tag_filter in store.find(
                BugSubscriptionFilterTag,
                BugSubscriptionFilterTag.filter == self))
        # Remove unused tags.
        for tag in set(current_tag_filters).difference(tags):
            tag_filter = current_tag_filters.pop(tag)
            store.remove(tag_filter)
        # Add additional tags.
        for tag in tags.difference(current_tag_filters):
            tag_filter = BugSubscriptionFilterTag()
            tag_filter.filter = self
            tag_filter.include = not tag.startswith("-")
            tag_filter.tag = tag.lstrip("-")
            store.add(tag_filter)

    tags = property(
        _get_tags, _set_tags, doc=(
            "A frozenset of tags filtered on."))

    def delete(self):
        """See `IBugSubscriptionFilter`."""
        self.importances = self.statuses = self.tags = ()
        Store.of(self).remove(self)
