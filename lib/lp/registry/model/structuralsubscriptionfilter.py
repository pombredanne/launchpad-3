# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'FilterSetBuilder',
    ]

from storm.expr import (
    And,
    CompoundOper,
    Except,
    In,
    Intersect,
    LeftJoin,
    NamedFunc,
    Not,
    Or,
    Select,
    SQL,
    Union,
    )

from canonical.database.sqlbase import quote
from lp.bugs.model.bugsubscriptionfilter import BugSubscriptionFilter
from lp.bugs.model.bugsubscriptionfilterimportance import (
    BugSubscriptionFilterImportance,
    )
from lp.bugs.model.bugsubscriptionfilterstatus import (
    BugSubscriptionFilterStatus,
    )
from lp.bugs.model.bugsubscriptionfiltertag import BugSubscriptionFilterTag
from lp.registry.model.structuralsubscription import StructuralSubscription


class ArrayAgg(NamedFunc):
    __slots__ = ()
    name = "ARRAY_AGG"


class Contains(CompoundOper):
    __slots__ = ()
    oper = "@>"


class FilterSetBuilder:
    """A convenience class to build queries for getSubscriptionsForBugTask."""

    def __init__(self, bugtask, level, join_condition):
        self.status = bugtask.status
        self.importance = bugtask.importance
        # The list() gets around some weirdness with security proxies; Storm
        # does not know how to compile an expression with a proxied list.
        self.tags = list(bugtask.bug.tags)
        # Set up common conditions.
        self.base_conditions = And(
            StructuralSubscription.bug_notification_level >= level,
            join_condition)
        # Set up common filter conditions.
        if len(self.tags) == 0:
            self.filter_conditions = And(
                BugSubscriptionFilter.include_any_tags == False,
                self.base_conditions)
        else:
            self.filter_conditions = And(
                BugSubscriptionFilter.exclude_any_tags == False,
                self.base_conditions)

    @property
    def subscriptions_without_filters(self):
        """Subscriptions without filters."""
        return Select(
            StructuralSubscription.id,
            tables=(
                StructuralSubscription,
                LeftJoin(
                    BugSubscriptionFilter,
                    BugSubscriptionFilter.structural_subscription_id == (
                        StructuralSubscription.id))),
            where=And(
                BugSubscriptionFilter.id == None,
                self.base_conditions))

    def _subscriptions_matching_x(self, join, extra_condition, **extra):
        return Select(
            StructuralSubscription.id,
            tables=(StructuralSubscription, BugSubscriptionFilter, join),
            where=And(
                BugSubscriptionFilter.structural_subscription_id == (
                    StructuralSubscription.id),
                self.filter_conditions,
                extra_condition),
            **extra)

    @property
    def subscriptions_matching_status(self):
        """Subscriptions with the given bugtask's status."""
        join = LeftJoin(
            BugSubscriptionFilterStatus,
            BugSubscriptionFilterStatus.filter_id == (
                BugSubscriptionFilter.id))
        condition = Or(
            BugSubscriptionFilterStatus.id == None,
            BugSubscriptionFilterStatus.status == self.status)
        return self._subscriptions_matching_x(join, condition)

    @property
    def subscriptions_matching_importance(self):
        """Subscriptions with the given bugtask's importance."""
        join = LeftJoin(
            BugSubscriptionFilterImportance,
            BugSubscriptionFilterImportance.filter_id == (
                BugSubscriptionFilter.id))
        condition = Or(
            BugSubscriptionFilterImportance.id == None,
            BugSubscriptionFilterImportance.importance == self.importance)
        return self._subscriptions_matching_x(join, condition)

    @property
    def subscriptions_tags_include_empty(self):
        """Subscriptions with no tags required."""
        join = LeftJoin(
            BugSubscriptionFilterTag,
            And(BugSubscriptionFilterTag.filter_id == (
                    BugSubscriptionFilter.id),
                BugSubscriptionFilterTag.include))
        return self._subscriptions_matching_x(
            join, BugSubscriptionFilterTag.id == None)

    @property
    def subscriptions_tags_include_match_any(self):
        """Subscriptions including any of the bug's tags."""
        condition = And(
            BugSubscriptionFilterTag.filter_id == (
                BugSubscriptionFilter.id),
            BugSubscriptionFilterTag.include,
            Not(BugSubscriptionFilter.find_all_tags),
            In(BugSubscriptionFilterTag.tag, self.tags))
        return self._subscriptions_matching_x(
            BugSubscriptionFilterTag, condition)

    @property
    def subscriptions_tags_exclude_match_any(self):
        """Subscriptions excluding any of the bug's tags."""
        condition = And(
            BugSubscriptionFilterTag.filter_id == (
                BugSubscriptionFilter.id),
            Not(BugSubscriptionFilterTag.include),
            Not(BugSubscriptionFilter.find_all_tags),
            In(BugSubscriptionFilterTag.tag, self.tags))
        return self._subscriptions_matching_x(
            BugSubscriptionFilterTag, condition)

    def _subscriptions_tags_match_all(self, extra_condition):
        tags_array = "ARRAY[%s]::TEXT[]" % ",".join(
            quote(tag) for tag in self.tags)
        return self._subscriptions_matching_x(
            BugSubscriptionFilterTag,
            And(
                BugSubscriptionFilterTag.filter_id == (
                    BugSubscriptionFilter.id),
                BugSubscriptionFilter.find_all_tags,
                self.filter_conditions,
                extra_condition),
            group_by=(
                StructuralSubscription.id,
                BugSubscriptionFilter.id),
            having=Contains(
                SQL(tags_array),
                ArrayAgg(BugSubscriptionFilterTag.tag)))

    @property
    def subscriptions_tags_include_match_all(self):
        """Subscriptions including the bug's tags."""
        return self._subscriptions_tags_match_all(
            BugSubscriptionFilterTag.include)

    @property
    def subscriptions_tags_exclude_match_all(self):
        """Subscriptions excluding the bug's tags."""
        return self._subscriptions_tags_match_all(
            Not(BugSubscriptionFilterTag.include))

    @property
    def subscriptions_tags_include(self):
        """Subscriptions with tag filters including the bug."""
        return Union(
            self.subscriptions_tags_include_empty,
            self.subscriptions_tags_include_match_any,
            self.subscriptions_tags_include_match_all)

    @property
    def subscriptions_tags_exclude(self):
        """Subscriptions with tag filters excluding the bug."""
        return Union(
            self.subscriptions_tags_exclude_match_any,
            self.subscriptions_tags_exclude_match_all)

    @property
    def subscriptions_tags_match(self):
        """Subscriptions with tag filters matching the bug."""
        if len(self.tags) == 0:
            # The subscription's required tags must be an empty set. The
            # subscription's excluded tags can be anything so no condition is
            # needed.
            return self.subscriptions_tags_include_empty
        else:
            return Except(
                self.subscriptions_tags_include,
                self.subscriptions_tags_exclude)

    @property
    def subscriptions_matching(self):
        """Subscriptions matching the bug."""
        return Union(
            self.subscriptions_without_filters,
            Intersect(
                self.subscriptions_matching_status,
                self.subscriptions_matching_importance,
                self.subscriptions_tags_match))
