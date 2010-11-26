# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'StructuralSubscription',
    'StructuralSubscriptionTargetMixin',
    ]

from sqlobject import ForeignKey
from storm.expr import (
    Alias,
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
from storm.store import Store
from zope.component import (
    adapts,
    getUtility,
    )
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (
    quote,
    SQLBase,
    )
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.interfaces.lpstorm import IStore
from lp.bugs.model.bugsubscriptionfilter import BugSubscriptionFilter
from lp.bugs.model.bugsubscriptionfilterimportance import (
    BugSubscriptionFilterImportance,
    )
from lp.bugs.model.bugsubscriptionfilterstatus import (
    BugSubscriptionFilterStatus,
    )
from lp.bugs.model.bugsubscriptionfiltertag import BugSubscriptionFilterTag
from lp.registry.enum import BugNotificationLevel
from lp.registry.errors import (
    DeleteSubscriptionError,
    UserCannotSubscribePerson,
    )
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.milestone import IMilestone
from lp.registry.interfaces.person import (
    validate_person,
    validate_public_person,
    )
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.projectgroup import IProjectGroup
from lp.registry.interfaces.structuralsubscription import (
    BlueprintNotificationLevel,
    IStructuralSubscription,
    IStructuralSubscriptionTarget,
    IStructuralSubscriptionTargetHelper,
    )
from lp.services.propertycache import cachedproperty


class StructuralSubscription(SQLBase):
    """A subscription to a Launchpad structure."""

    implements(IStructuralSubscription)

    _table = 'StructuralSubscription'

    product = ForeignKey(
        dbName='product', foreignKey='Product', notNull=False, default=None)
    productseries = ForeignKey(
        dbName='productseries', foreignKey='ProductSeries', notNull=False,
        default=None)
    project = ForeignKey(
        dbName='project', foreignKey='ProjectGroup', notNull=False,
        default=None)
    milestone = ForeignKey(
        dbName='milestone', foreignKey='Milestone', notNull=False,
        default=None)
    distribution = ForeignKey(
        dbName='distribution', foreignKey='Distribution', notNull=False,
        default=None)
    distroseries = ForeignKey(
        dbName='distroseries', foreignKey='DistroSeries', notNull=False,
        default=None)
    sourcepackagename = ForeignKey(
        dbName='sourcepackagename', foreignKey='SourcePackageName',
        notNull=False, default=None)
    subscriber = ForeignKey(
        dbName='subscriber', foreignKey='Person',
        storm_validator=validate_person, notNull=True)
    subscribed_by = ForeignKey(
        dbName='subscribed_by', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    bug_notification_level = EnumCol(
        enum=BugNotificationLevel,
        default=BugNotificationLevel.NOTHING,
        notNull=True)
    blueprint_notification_level = EnumCol(
        enum=BlueprintNotificationLevel,
        default=BlueprintNotificationLevel.NOTHING,
        notNull=True)
    date_created = UtcDateTimeCol(
        dbName='date_created', notNull=True, default=UTC_NOW)
    date_last_updated = UtcDateTimeCol(
        dbName='date_last_updated', notNull=True, default=UTC_NOW)

    @property
    def target(self):
        """See `IStructuralSubscription`."""
        if self.product is not None:
            return self.product
        elif self.productseries is not None:
            return self.productseries
        elif self.project is not None:
            return self.project
        elif self.milestone is not None:
            return self.milestone
        elif self.distribution is not None:
            if self.sourcepackagename is not None:
                # XXX intellectronica 2008-01-15:
                #   We're importing this pseudo db object
                #   here because importing it from the top
                #   doesn't play well with the loading
                #   sequence.
                from lp.registry.model.distributionsourcepackage import (
                    DistributionSourcePackage)
                return DistributionSourcePackage(
                    self.distribution, self.sourcepackagename)
            else:
                return self.distribution
        elif self.distroseries is not None:
            return self.distroseries
        else:
            raise AssertionError('StructuralSubscription has no target.')

    @property
    def bug_filters(self):
        """See `IStructuralSubscription`."""
        return IStore(BugSubscriptionFilter).find(
            BugSubscriptionFilter,
            BugSubscriptionFilter.structural_subscription == self)

    def newBugFilter(self):
        """See `IStructuralSubscription`."""
        bug_filter = BugSubscriptionFilter()
        bug_filter.structural_subscription = self
        return bug_filter


class DistroSeriesTargetHelper:
    """A helper for `IDistroSeries`s."""

    implements(IStructuralSubscriptionTargetHelper)
    adapts(IDistroSeries)

    target_type_display = 'distribution series'

    def __init__(self, target):
        self.target = target
        self.target_parent = target.distribution
        self.target_arguments = {"distroseries": target}
        self.pillar = target.distribution
        self.join = (StructuralSubscription.distroseries == target)


class ProjectGroupTargetHelper:
    """A helper for `IProjectGroup`s."""

    implements(IStructuralSubscriptionTargetHelper)
    adapts(IProjectGroup)

    target_type_display = 'project group'

    def __init__(self, target):
        self.target = target
        self.target_parent = None
        self.target_arguments = {"project": target}
        self.pillar = target
        self.join = (StructuralSubscription.project == target)


class DistributionSourcePackageTargetHelper:
    """A helper for `IDistributionSourcePackage`s."""

    implements(IStructuralSubscriptionTargetHelper)
    adapts(IDistributionSourcePackage)

    target_type_display = 'package'

    def __init__(self, target):
        self.target = target
        self.target_parent = target.distribution
        self.target_arguments = {
            "distribution": target.distribution,
            "sourcepackagename": target.sourcepackagename,
            }
        self.pillar = target.distribution
        self.join = And(
            StructuralSubscription.distributionID == (
                target.distribution.id),
            StructuralSubscription.sourcepackagenameID == (
                target.sourcepackagename.id))


class MilestoneTargetHelper:
    """A helper for `IMilestone`s."""

    implements(IStructuralSubscriptionTargetHelper)
    adapts(IMilestone)

    target_type_display = 'milestone'

    def __init__(self, target):
        self.target = target
        self.target_parent = target.target
        self.target_arguments = {"milestone": target}
        self.pillar = target.target
        self.join = (StructuralSubscription.milestone == target)


class ProductTargetHelper:
    """A helper for `IProduct`s."""

    implements(IStructuralSubscriptionTargetHelper)
    adapts(IProduct)

    target_type_display = 'project'

    def __init__(self, target):
        self.target = target
        self.target_parent = target.project
        self.target_arguments = {"product": target}
        self.pillar = target
        self.join = (StructuralSubscription.product == target)


class ProductSeriesTargetHelper:
    """A helper for `IProductSeries`s."""

    implements(IStructuralSubscriptionTargetHelper)
    adapts(IProductSeries)

    target_type_display = 'project series'

    def __init__(self, target):
        self.target = target
        self.target_parent = target.product
        self.target_arguments = {"productseries": target}
        self.pillar = target.product
        self.join = (StructuralSubscription.productseries == target)


class DistributionTargetHelper:
    """A helper for `IDistribution`s."""

    implements(IStructuralSubscriptionTargetHelper)
    adapts(IDistribution)

    target_type_display = 'distribution'

    def __init__(self, target):
        self.target = target
        self.target_parent = None
        self.target_arguments = {
            "distribution": target,
            "sourcepackagename": None,
            }
        self.pillar = target
        self.join = And(
            StructuralSubscription.distributionID == target.id,
            StructuralSubscription.sourcepackagenameID == None)


class StructuralSubscriptionTargetMixin:
    """Mixin class for implementing `IStructuralSubscriptionTarget`."""

    @cachedproperty
    def __helper(self):
        """A `IStructuralSubscriptionTargetHelper` for this object.

        Eventually this helper object could become *the* way to work with
        structural subscriptions. For now it just provides a few bits that
        vary with the context.

        It is cached in a pseudo-private variable because this is a mixin
        class.
        """
        return IStructuralSubscriptionTargetHelper(self)

    @property
    def _target_args(self):
        """Target Arguments.

        Return a dictionary with the arguments representing this
        target in a call to the structural subscription constructor.
        """
        return self.__helper.target_arguments

    @property
    def parent_subscription_target(self):
        """See `IStructuralSubscriptionTarget`."""
        parent = self.__helper.target_parent
        assert (parent is None or
                IStructuralSubscriptionTarget.providedBy(parent))
        return parent

    @property
    def target_type_display(self):
        """See `IStructuralSubscriptionTarget`."""
        return self.__helper.target_type_display

    def userCanAlterSubscription(self, subscriber, subscribed_by):
        """See `IStructuralSubscriptionTarget`."""
        # A Launchpad administrator or the user can subscribe a user.
        # A Launchpad or team admin can subscribe a team.

        # Nobody else can, unless the context is a IDistributionSourcePackage,
        # in which case the drivers or owner can.
        if IDistributionSourcePackage.providedBy(self):
            for driver in self.distribution.drivers:
                if subscribed_by.inTeam(driver):
                    return True
            if subscribed_by.inTeam(self.distribution.owner):
                return True

        admins = getUtility(ILaunchpadCelebrities).admin
        return (subscriber == subscribed_by or
                subscriber in subscribed_by.getAdministratedTeams() or
                subscribed_by.inTeam(admins))

    def addSubscription(self, subscriber, subscribed_by):
        """See `IStructuralSubscriptionTarget`."""
        if subscriber is None:
            subscriber = subscribed_by

        if not self.userCanAlterSubscription(subscriber, subscribed_by):
            raise UserCannotSubscribePerson(
                '%s does not have permission to subscribe %s.' % (
                    subscribed_by.name, subscriber.name))

        existing_subscription = self.getSubscription(subscriber)

        if existing_subscription is not None:
            return existing_subscription
        else:
            return StructuralSubscription(
                subscriber=subscriber,
                subscribed_by=subscribed_by,
                **self._target_args)

    def userCanAlterBugSubscription(self, subscriber, subscribed_by):
        """See `IStructuralSubscriptionTarget`."""

        admins = getUtility(ILaunchpadCelebrities).admin
        # If the object to be structurally subscribed to for bug
        # notifications is a distribution and that distribution has a
        # bug supervisor then only the bug supervisor or a member of
        # that team or, of course, admins, can subscribe someone to it.
        if IDistribution.providedBy(self) and self.bug_supervisor is not None:
            if subscriber is None or subscribed_by is None:
                return False
            elif (subscriber != self.bug_supervisor
                and not subscriber.inTeam(self.bug_supervisor)
                and not subscribed_by.inTeam(admins)):
                return False
        return True

    def addBugSubscription(self, subscriber, subscribed_by,
                           bug_notification_level=None):
        """See `IStructuralSubscriptionTarget`."""
        # This is a helper method for creating a structural
        # subscription and immediately giving it a full
        # bug notification level. It is useful so long as
        # subscriptions are mainly used to implement bug contacts.

        if not self.userCanAlterBugSubscription(subscriber, subscribed_by):
            raise UserCannotSubscribePerson(
                '%s does not have permission to subscribe %s' % (
                    subscribed_by.name, subscriber.name))

        sub = self.addSubscription(subscriber, subscribed_by)
        if bug_notification_level is None:
            bug_notification_level = BugNotificationLevel.COMMENTS
        sub.bug_notification_level = bug_notification_level
        return sub

    def removeBugSubscription(self, subscriber, unsubscribed_by):
        """See `IStructuralSubscriptionTarget`."""
        if subscriber is None:
            subscriber = unsubscribed_by

        if not self.userCanAlterSubscription(subscriber, unsubscribed_by):
            raise UserCannotSubscribePerson(
                '%s does not have permission to unsubscribe %s.' % (
                    unsubscribed_by.name, subscriber.name))

        subscription_to_remove = None
        for subscription in self.getSubscriptions(
            min_bug_notification_level=BugNotificationLevel.METADATA):
            # Only search for bug subscriptions
            if subscription.subscriber == subscriber:
                subscription_to_remove = subscription
                break

        if subscription_to_remove is None:
            raise DeleteSubscriptionError(
                "%s is not subscribed to %s." % (
                subscriber.name, self.displayname))
        else:
            if (subscription_to_remove.blueprint_notification_level >
                BlueprintNotificationLevel.NOTHING):
                # This is a subscription to other application too
                # so only set the bug notification level
                subscription_to_remove.bug_notification_level = (
                    BugNotificationLevel.NOTHING)
            else:
                subscription_to_remove.destroySelf()

    def getSubscription(self, person):
        """See `IStructuralSubscriptionTarget`."""
        all_subscriptions = self.getSubscriptions()
        for subscription in all_subscriptions:
            if subscription.subscriber == person:
                return subscription
        return None

    def getSubscriptions(self,
                         min_bug_notification_level=
                         BugNotificationLevel.NOTHING,
                         min_blueprint_notification_level=
                         BlueprintNotificationLevel.NOTHING):
        """See `IStructuralSubscriptionTarget`."""
        clauses = [
            "StructuralSubscription.subscriber = Person.id",
            "StructuralSubscription.bug_notification_level "
            ">= %s" % quote(min_bug_notification_level),
            "StructuralSubscription.blueprint_notification_level "
            ">= %s" % quote(min_blueprint_notification_level),
            ]
        for key, value in self._target_args.iteritems():
            if value is None:
                clauses.append(
                    "StructuralSubscription.%s IS NULL" % (key,))
            else:
                clauses.append(
                    "StructuralSubscription.%s = %s" % (key, quote(value)))
        query = " AND ".join(clauses)
        return StructuralSubscription.select(
            query, orderBy='Person.displayname', clauseTables=['Person'])

    @property
    def bug_subscriptions(self):
        """See `IStructuralSubscriptionTarget`."""
        return self.getSubscriptions(
            min_bug_notification_level=BugNotificationLevel.METADATA)

    def userHasBugSubscriptions(self, user):
        """See `IStructuralSubscriptionTarget`."""
        bug_subscriptions = self.getSubscriptions(
            min_bug_notification_level=BugNotificationLevel.METADATA)
        if user is not None:
            for subscription in bug_subscriptions:
                if (subscription.subscriber == user or
                    user.inTeam(subscription.subscriber)):
                    # The user has a bug subscription
                    return True
        return False

    def getSubscriptionsForBugTask(self, bugtask, level):
        """See `IStructuralSubscriptionTarget`."""
        set_builder = BugFilterSetBuilder(
            bugtask, level, self.__helper.join)
        return Store.of(self.__helper.pillar).find(
            StructuralSubscription, In(
                StructuralSubscription.id,
                set_builder.subscriptions))


class ArrayAgg(NamedFunc):
    __slots__ = ()
    name = "ARRAY_AGG"


class ArrayContains(CompoundOper):
    __slots__ = ()
    oper = "@>"


class BugFilterSetBuilder:
    """A convenience class to build queries for getSubscriptionsForBugTask."""

    def __init__(self, bugtask, level, join_condition):
        """Initialize a new set builder for bug filters.

        :param bugtask: The `IBugTask` to match against.
        :param level: A member of `BugNotificationLevel`.
        :param join_condition: A condition for selecting structural
            subscriptions. Generally this should limit the subscriptions to a
            particular target (i.e. project or distribution).
        """
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
                # When the bug has no tags, filters with include_any_tags set
                # can never match.
                Not(BugSubscriptionFilter.include_any_tags),
                self.base_conditions)
        else:
            self.filter_conditions = And(
                # When the bug has tags, filters with exclude_any_tags set can
                # never match.
                Not(BugSubscriptionFilter.exclude_any_tags),
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

    def _filters_matching_x(self, join, where_condition, **extra):
        """Return an expression yielding `(subscription_id, filter_id)` rows.

        The expressions returned by this function are used in set (union,
        intersect, except) operations at the *filter* level. However, the
        interesting result of these set operations is the structural
        subscription, hence both columns are included in the expressions
        generated. Since a structural subscription can have zero or more
        filters, and a filter can never be associated with more than one
        subscription, the set operations are unaffected.
        """
        return Select(
            columns=(
                # Alias this column so it can be selected in
                # subscriptions_matching.
                Alias(
                    BugSubscriptionFilter.structural_subscription_id,
                    "structural_subscription_id"),
                BugSubscriptionFilter.id),
            tables=(
                StructuralSubscription, BugSubscriptionFilter, join),
            where=And(
                BugSubscriptionFilter.structural_subscription_id == (
                    StructuralSubscription.id),
                self.filter_conditions,
                where_condition),
            **extra)

    @property
    def filters_matching_status(self):
        """Filters with the given bugtask's status."""
        join = LeftJoin(
            BugSubscriptionFilterStatus,
            BugSubscriptionFilterStatus.filter_id == (
                BugSubscriptionFilter.id))
        condition = Or(
            BugSubscriptionFilterStatus.id == None,
            BugSubscriptionFilterStatus.status == self.status)
        return self._filters_matching_x(join, condition)

    @property
    def filters_matching_importance(self):
        """Filters with the given bugtask's importance."""
        join = LeftJoin(
            BugSubscriptionFilterImportance,
            BugSubscriptionFilterImportance.filter_id == (
                BugSubscriptionFilter.id))
        condition = Or(
            BugSubscriptionFilterImportance.id == None,
            BugSubscriptionFilterImportance.importance == self.importance)
        return self._filters_matching_x(join, condition)

    @property
    def filters_without_include_tags(self):
        """Filters with no tags required."""
        join = LeftJoin(
            BugSubscriptionFilterTag,
            And(BugSubscriptionFilterTag.filter_id == (
                    BugSubscriptionFilter.id),
                BugSubscriptionFilterTag.include))
        return self._filters_matching_x(
            join, BugSubscriptionFilterTag.id == None)

    @property
    def filters_matching_any_include_tags(self):
        """Filters including any of the bug's tags."""
        condition = And(
            BugSubscriptionFilterTag.filter_id == (
                BugSubscriptionFilter.id),
            BugSubscriptionFilterTag.include,
            Not(BugSubscriptionFilter.find_all_tags),
            In(BugSubscriptionFilterTag.tag, self.tags))
        return self._filters_matching_x(
            BugSubscriptionFilterTag, condition)

    @property
    def filters_matching_any_exclude_tags(self):
        """Filters excluding any of the bug's tags."""
        condition = And(
            BugSubscriptionFilterTag.filter_id == (
                BugSubscriptionFilter.id),
            Not(BugSubscriptionFilterTag.include),
            Not(BugSubscriptionFilter.find_all_tags),
            In(BugSubscriptionFilterTag.tag, self.tags))
        return self._filters_matching_x(
            BugSubscriptionFilterTag, condition)

    def _filters_matching_all_x_tags(self, where_condition):
        """Return an expression yielding `(subscription_id, filter_id)` rows.

        This joins to `BugSubscriptionFilterTag` and calls up to
        `_filters_matching_x`, and groups by filter. Conditions are added to
        ensure that all rows in each group are a subset of the bug's tags.
        """
        tags_array = "ARRAY[%s]::TEXT[]" % ",".join(
            quote(tag) for tag in self.tags)
        return self._filters_matching_x(
            BugSubscriptionFilterTag,
            And(
                BugSubscriptionFilterTag.filter_id == (
                    BugSubscriptionFilter.id),
                BugSubscriptionFilter.find_all_tags,
                self.filter_conditions,
                where_condition),
            group_by=(
                BugSubscriptionFilter.structural_subscription_id,
                BugSubscriptionFilter.id),
            having=ArrayContains(
                SQL(tags_array), ArrayAgg(
                    BugSubscriptionFilterTag.tag)))

    @property
    def filters_matching_all_include_tags(self):
        """Filters including the bug's tags."""
        return self._filters_matching_all_x_tags(
            BugSubscriptionFilterTag.include)

    @property
    def filters_matching_all_exclude_tags(self):
        """Filters excluding the bug's tags."""
        return self._filters_matching_all_x_tags(
            Not(BugSubscriptionFilterTag.include))

    @property
    def filters_matching_include_tags(self):
        """Filters with tag filters including the bug."""
        return Union(
            self.filters_matching_any_include_tags,
            self.filters_matching_all_include_tags)

    @property
    def filters_matching_exclude_tags(self):
        """Filters with tag filters excluding the bug."""
        return Union(
            self.filters_matching_any_exclude_tags,
            self.filters_matching_all_exclude_tags)

    @property
    def filters_matching_tags(self):
        """Filters with tag filters matching the bug."""
        if len(self.tags) == 0:
            # The filter's required tags must be an empty set. The filter's
            # excluded tags can be anything so no condition is needed.
            return self.filters_without_include_tags
        else:
            return Except(
                Union(self.filters_without_include_tags,
                      self.filters_matching_include_tags),
                self.filters_matching_exclude_tags)

    @property
    def filters_matching(self):
        """Filters matching the bug."""
        return Intersect(
            self.filters_matching_status,
            self.filters_matching_importance,
            self.filters_matching_tags)

    @property
    def subscriptions_with_matching_filters(self):
        """Subscriptions with one or more filters matching the bug."""
        return Select(
            # I don't know of a more Storm-like way of doing this.
            SQL("filters_matching.structural_subscription_id"),
            tables=Alias(self.filters_matching, "filters_matching"))

    @property
    def subscriptions(self):
        return Union(
            self.subscriptions_without_filters,
            self.subscriptions_with_matching_filters)
