# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'get_all_structural_subscriptions',
    'get_structural_subscribers_for_bugtasks',
    'get_structural_subscription_targets',
    'StructuralSubscription',
    'StructuralSubscriptionTargetMixin',
    ]

import pytz

from storm.locals import (
    DateTime,
    Int,
    Reference,
    )

from storm.base import Storm
from storm.expr import (
    And,
    CompoundOper,
    Count,
    In,
    Join,
    LeftJoin,
    NamedFunc,
    Not,
    Or,
    Select,
    SQL,
    Union,
    )
from storm.store import (
    Store,
    EmptyResultSet,
    )
from zope.component import (
    adapts,
    getUtility,
    )
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import quote
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.interfaces.lpstorm import IStore
from lp.bugs.interfaces.structuralsubscription import (
    IStructuralSubscription,
    IStructuralSubscriptionTarget,
    IStructuralSubscriptionTargetHelper,
    )
from lp.bugs.model.bugsubscription import BugSubscription
from lp.bugs.model.bugsubscriptionfilter import BugSubscriptionFilter
from lp.bugs.model.bugsubscriptionfilterimportance import (
    BugSubscriptionFilterImportance,
    )
from lp.bugs.model.bugsubscriptionfilterstatus import (
    BugSubscriptionFilterStatus,
    )
from lp.bugs.model.bugsubscriptionfiltertag import BugSubscriptionFilterTag
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
from lp.registry.interfaces.sourcepackage import ISourcePackage
from lp.services.propertycache import cachedproperty


class StructuralSubscription(Storm):
    """A subscription to a Launchpad structure."""

    implements(IStructuralSubscription)

    __storm_table__ = 'StructuralSubscription'

    id = Int(primary=True)

    productID = Int("product", default=None)
    product = Reference(productID, "Product.id")

    productseriesID = Int("productseries", default=None)
    productseries = Reference(productseriesID, "ProductSeries.id")

    projectID = Int("project", default=None)
    project = Reference(projectID, "ProjectGroup.id")

    milestoneID = Int("milestone", default=None)
    milestone = Reference(milestoneID, "Milestone.id")

    distributionID = Int("distribution", default=None)
    distribution = Reference(distributionID, "Distribution.id")

    distroseriesID = Int("distroseries", default=None)
    distroseries = Reference(distroseriesID, "DistroSeries.id")

    sourcepackagenameID = Int("sourcepackagename", default=None)
    sourcepackagename = Reference(sourcepackagenameID, "SourcePackageName.id")

    subscriberID = Int("subscriber", allow_none=False,
                        validator=validate_person)
    subscriber = Reference(subscriberID, "Person.id")

    subscribed_byID = Int("subscribed_by", allow_none=False,
                          validator=validate_public_person)
    subscribed_by = Reference(subscribed_byID, "Person.id")

    date_created = DateTime(
        "date_created", allow_none=False, default=UTC_NOW,
        tzinfo=pytz.UTC)
    date_last_updated = DateTime(
        "date_last_updated", allow_none=False, default=UTC_NOW,
        tzinfo=pytz.UTC)

    def __init__(self, subscriber, subscribed_by, **kwargs):
        self.subscriber = subscriber
        self.subscribed_by = subscribed_by
        for arg, value in kwargs.iteritems():
            setattr(self, arg, value)

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
        # This flush is needed for the web service API.
        IStore(StructuralSubscription).flush()
        return bug_filter

    def delete(self):
        store = Store.of(self)
        self.bug_filters.remove()
        store.remove(self)


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
            new_subscription = StructuralSubscription(
                subscriber=subscriber,
                subscribed_by=subscribed_by,
                **self._target_args)
            subscription_filter = new_subscription.newBugFilter()
            return new_subscription

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

    def addBugSubscription(self, subscriber, subscribed_by):
        """See `IStructuralSubscriptionTarget`."""
        # This is a helper method for creating a structural
        # subscription. It is useful so long as subscriptions are mainly
        # used to implement bug contacts.

        if not self.userCanAlterBugSubscription(subscriber, subscribed_by):
            raise UserCannotSubscribePerson(
                '%s does not have permission to subscribe %s' % (
                    subscribed_by.name, subscriber.name))

        return self.addSubscription(subscriber, subscribed_by)

    def removeBugSubscription(self, subscriber, unsubscribed_by):
        """See `IStructuralSubscriptionTarget`."""
        if subscriber is None:
            subscriber = unsubscribed_by

        if not self.userCanAlterSubscription(subscriber, unsubscribed_by):
            raise UserCannotSubscribePerson(
                '%s does not have permission to unsubscribe %s.' % (
                    unsubscribed_by.name, subscriber.name))

        subscription_to_remove = self.getSubscriptions(
            subscriber=subscriber).one()

        if subscription_to_remove is None:
            raise DeleteSubscriptionError(
                "%s is not subscribed to %s." % (
                subscriber.name, self.displayname))
        subscription_to_remove.delete()

    def getSubscription(self, person):
        """See `IStructuralSubscriptionTarget`."""
        # getSubscriptions returns all subscriptions regardless of
        # the person for person==None, so we special-case that.
        if person is None:
            return None
        all_subscriptions = self.getSubscriptions(subscriber=person)
        return all_subscriptions.one()

    def getSubscriptions(self, subscriber=None):
        """See `IStructuralSubscriptionTarget`."""
        from lp.registry.model.person import Person
        clauses = [StructuralSubscription.subscriberID==Person.id]
        for key, value in self._target_args.iteritems():
            clauses.append(
                getattr(StructuralSubscription, key)==value)

        if subscriber is not None:
            clauses.append(
                StructuralSubscription.subscriberID==subscriber.id)

        store = Store.of(self.__helper.pillar)
        return store.find(
            StructuralSubscription, *clauses).order_by('Person.displayname')

    @property
    def bug_subscriptions(self):
        """See `IStructuralSubscriptionTarget`."""
        return self.getSubscriptions()

    def userHasBugSubscriptions(self, user):
        """See `IStructuralSubscriptionTarget`."""
        bug_subscriptions = self.getSubscriptions()
        if user is not None:
            for subscription in bug_subscriptions:
                if (subscription.subscriber == user or
                    user.inTeam(subscription.subscriber)):
                    # The user has a bug subscription
                    return True
        return False

    def getSubscriptionsForBugTask(self, bugtask, level):
        """See `IStructuralSubscriptionTarget`."""
        # Note that this method does not take into account
        # structural subscriptions without filters.  Since it is only
        # used for tests at this point, that's not a problem; moreover,
        # we intend all structural subscriptions to have filters.
        candidates, filter_id_query = (
            _get_structural_subscription_filter_id_query(
                bugtask.bug, [bugtask], level))
        if not candidates:
            return EmptyResultSet()
        return IStore(StructuralSubscription).find(
            StructuralSubscription,
            BugSubscriptionFilter.structural_subscription_id ==
            StructuralSubscription.id,
            In(BugSubscriptionFilter.id,
               filter_id_query)).config(distinct=True)


def get_structural_subscription_targets(bugtasks):
    """Return (bugtask, target) pairs for each target of the bugtasks.

    Each bugtask may be responsible theoretically for 0 or more targets.
    In practice, each generates one, two or three.
    """
    for bugtask in bugtasks:
        if IStructuralSubscriptionTarget.providedBy(bugtask.target):
            yield (bugtask, bugtask.target)
            if bugtask.target.parent_subscription_target is not None:
                yield (bugtask, bugtask.target.parent_subscription_target)
        # This can probably be an elif.  Determining conclusively
        # whether it can be is not a priority at this time.  The
        # docstring says one, two, or three targets per bugtask because
        # of the belief that this could be an elif; otherwise, it would
        # be one, two, three or four.
        if ISourcePackage.providedBy(bugtask.target):
            # Distribution series bug tasks with a package have the source
            # package set as their target, so we add the distroseries
            # explicitly to the set of subscription targets.
            yield (bugtask, bugtask.distroseries)
        if bugtask.milestone is not None:
            yield (bugtask, bugtask.milestone)


def _get_all_structural_subscriptions(find, targets, *conditions):
    """Find the structural subscriptions for the given targets.

    :param find: what to find (typically StructuralSubscription or
                 StructuralSubscription.id).
    :param targets: an iterable of (bugtask, target) pairs, as returned by
                    get_structural_subscription_targets.
    :param conditions: additional conditions to filter the results.
    """
    targets = set(target for bugtask, target in targets)
    target_descriptions = [
        IStructuralSubscriptionTargetHelper(target).join
        for target in targets]
    return list(
        IStore(StructuralSubscription).find(
            find, Or(*target_descriptions), *conditions))


def get_all_structural_subscriptions(bugtasks, person=None):
    if not bugtasks:
        return EmptyResultSet()
    conditions = []
    if person is not None:
        conditions.append(
            StructuralSubscription.subscriber == person)
    return _get_all_structural_subscriptions(
        StructuralSubscription,
        get_structural_subscription_targets(bugtasks),
        *conditions)


def _get_structural_subscribers(candidates, filter_id_query, recipients):
    if not candidates:
        return EmptyResultSet()
    # This is here because of a circular import.
    from lp.registry.model.person import Person
    source = IStore(StructuralSubscription).using(
        StructuralSubscription,
        # XXX gary 2011-03-03 bug 728818
        # We need to do this LeftJoin because we still have structural
        # subscriptions without filters in qastaging and production.
        # Once we do not, we can just use a Join.  Also see constraints
        # below.
        LeftJoin(BugSubscriptionFilter,
             BugSubscriptionFilter.structural_subscription_id ==
             StructuralSubscription.id),
        Join(Person,
             Person.id == StructuralSubscription.subscriberID),
        )
    constraints = [
        # XXX gary 2011-03-03 bug 728818
        # We need to do this Or because we still have structural
        # subscriptions without filters in qastaging and production.
        # Once we do not, we can simplify this to just
        # "In(BugSubscriptionFilter.id, filter_id_query)".  Also see
        # LeftJoin above.
        Or(In(BugSubscriptionFilter.id, filter_id_query),
           And(In(StructuralSubscription.id, candidates),
               BugSubscriptionFilter.id == None))]
    if recipients is None:
        return source.find(
            Person, *constraints).config(distinct=True).order_by()
    else:
        subscribers = []
        query_results = source.find(
            (Person, StructuralSubscription),
            *constraints).config(distinct=True)
        for person, subscription in query_results:
            # Set up results.
            if person not in recipients:
                subscribers.append(person)
                recipients.addStructuralSubscriber(
                    person, subscription.target)
        return subscribers


def get_structural_subscribers_for_bugtasks(bugtasks,
                                            recipients=None,
                                            level=None):
    """Return subscribers for structural filters for the bugtasks at "level".

    :param bugtasks: an iterable of bugtasks.  All must be for the same bug.
    :param recipients: a BugNotificationRecipients object or None.
                       Populates if given.
    :param level: a level from lp.bugs.enum.BugNotificationLevel.

    Excludes structural subscriptions for people who are directly subscribed
    to the bug."""
    if not bugtasks:
        return EmptyResultSet()
    bugs = set(bugtask.bug for bugtask in bugtasks)
    if len(bugs) > 1:
        raise NotImplementedError('Each bugtask must be from the same bug.')
    bug = bugs.pop()
    candidates, query = _get_structural_subscription_filter_id_query(
        bug, bugtasks, level)
    return _get_structural_subscribers(candidates, query, recipients)


class ArrayAgg(NamedFunc):
    "Aggregate values (within a GROUP BY) into an array."
    __slots__ = ()
    name = "ARRAY_AGG"


class ArrayContains(CompoundOper):
    "True iff the left side is a superset of the right side."
    __slots__ = ()
    oper = "@>"


class ArrayIntersects(CompoundOper):
    "True iff the left side shares at least one element with the right side."
    __slots__ = ()
    oper = "&&"


def _get_structural_subscription_filter_id_query(bug, bugtasks, level):
    """Helper function.

    This provides the core implementation for
    get_structural_subscribers_for_bug and
    get_structural_subscribers_for_bugtask.
    
    :param bug: a bug.
    :param bugtasks: an iterable of one or more bugtasks of the bug.
    :param level: a notification level.
    """
    # We get the ids because we need to use group by in order to
    # look at the filters' tags in aggregate.  Once we have the ids,
    # we can get the full set of what we need in subsuming or
    # subsequent SQL calls.
    # (Aside 1: We could in theory get all the fields we wanted with
    # a hack--we could use an aggregrate function like max to get
    # fields that we know will be unique--but Storm would not like
    # it.)
    # (Aside 2: IMO Postgres should allow getting other fields if
    # the group-by key is a primary key and the other fields desired
    # are other values from the same table as the group-by key, or
    # values of a table linked by a foreign key from the same table
    # as the group-by key...but that's dreaming.)
    # See the docstring of get_structural_subscription_targets.
    query_arguments = list(
        get_structural_subscription_targets(bugtasks))
    assert len(query_arguments) > 0, (
        'Programmer error: expected query arguments')
    # With large numbers of filters in the system, it's fastest in our
    # tests if we get a set of structural subscriptions pertinent to the
    # given targets, and then work with that.  It also comes in handy
    # when we have to do a union, because we can share the work across
    # the two queries.
    # We will exclude people who have a direct subscription to the bug.
    filters = [
        Not(In(StructuralSubscription.subscriberID,
               Select(BugSubscription.person_id,
                      BugSubscription.bug == bug)))]
    candidates = _get_all_structural_subscriptions(
        StructuralSubscription.id, query_arguments, *filters)
    if not candidates:
        # If there are no structural subscriptions for these targets,
        # then we don't need to look at the importance, status, and
        # tags.  We're done.
        return None, None
    # The "select_args" dictionary holds the arguments that we will
    # pass to one or more SELECT clauses.  We start with what will
    # become the FROM clause.  We always want the following Joins,
    # so we can add them here at the beginning.
    select_args = {
        'tables': [
            StructuralSubscription,
            Join(BugSubscriptionFilter,
                 BugSubscriptionFilter.structural_subscription_id ==
                 StructuralSubscription.id),
            LeftJoin(BugSubscriptionFilterStatus,
                     BugSubscriptionFilterStatus.filter_id ==
                     BugSubscriptionFilter.id),
            LeftJoin(BugSubscriptionFilterImportance,
                     BugSubscriptionFilterImportance.filter_id ==
                     BugSubscriptionFilter.id),
            LeftJoin(BugSubscriptionFilterTag,
                     BugSubscriptionFilterTag.filter_id ==
                     BugSubscriptionFilter.id)]}
    # The "conditions" list will eventually be passed to a Storm
    # "And" function, and then become the WHERE clause of our SELECT.
    conditions = [In(StructuralSubscription.id, candidates)]
    # Handling notification level is trivial, so we include that first.
    if level is not None:
        conditions.append(
            BugSubscriptionFilter.bug_notification_level >= level)
    # Now we handle importance and status, which are per bugtask.
    # What we do is loop through the collection of bugtask, target
    # in query_arguments.  Each bugtask will have one or more
    # targets that we have to check.  We figure out how to describe each
    # target using the useful IStructuralSubscriptionTargetHelper
    # adapter, which has a "join" attribute on it that tells us how
    # to distinguish that target.  Once we have all of the target
    # descriptins, we OR those together, and say that the filters
    # for those targets must either have no importance or match the
    # associated bugtask's importance; and have no status or match
    # the bugtask's status.  Once we have looked at all of the
    # bugtasks, we OR all of those per-bugtask target comparisons
    # together, and we are done with the status and importance.
    # The "outer_or_conditions" list holds the full clauses for each
    # bugtask.
    outer_or_conditions = []
    # The "or_target_conditions" list holds the clauses for each target,
    # and is reset for each new bugtask.
    or_target_conditions = []

    def handle_bugtask_conditions(bugtask):
        """Helper function for building status and importance clauses.

        Call with the previous bugtask when the bugtask changes in
        the iteration of query_arguments, and call with the last
        bugtask when the iteration is complete."""
        if or_target_conditions:
            outer_or_conditions.append(
                And(Or(*or_target_conditions),
                    Or(BugSubscriptionFilterImportance.importance ==
                       bugtask.importance,
                       BugSubscriptionFilterImportance.importance == None),
                    Or(BugSubscriptionFilterStatus.status == bugtask.status,
                       BugSubscriptionFilterStatus.status == None)))
            del or_target_conditions[:]
    last_bugtask = None
    for bugtask, target in query_arguments:
        if last_bugtask is not bugtask:
            handle_bugtask_conditions(last_bugtask)
        last_bugtask = bugtask
        or_target_conditions.append(
            IStructuralSubscriptionTargetHelper(target).join)
    # We know there will be at least one bugtask, because we already
    # escaped early "if len(query_arguments) == 0".
    handle_bugtask_conditions(bugtask)
    conditions.append(Or(*outer_or_conditions))
    # Now we handle tags.  If the bug has no tags, this is
    # relatively easy. Otherwise, not so much.
    tags = list(bug.tags) # This subtly removes the security proxy on
    # the list.  Strings are never security-proxied, so we don't have
    # to worry about them.
    if len(tags) == 0:
        # The bug has no tags.  We should leave out filters that
        # require any generic non-empty set of tags
        # (BugSubscriptionFilter.include_any_tags), which we do with
        # the conditions.  Then we can finish up the WHERE clause.
        # Then we have to make sure that the filter does not require
        # any *specific* tags. We do that with a GROUP BY on the
        # filters, and then a HAVING clause that aggregates the
        # BugSubscriptionFilterTags that are set to "include" the
        # tag.  (If it is not an include, that is an exclude, and a
        # bug without tags will not have a particular tag, so we can
        # ignore those in this case.)  This requires a CASE
        # statement within the COUNT.  After this, we are done, and
        # we return the fully formed SELECT query object.
        conditions.append(Not(BugSubscriptionFilter.include_any_tags))
        select_args['where'] = And(*conditions)
        select_args['group_by'] = (BugSubscriptionFilter.id,)
        select_args['having'] = Count(
            SQL('CASE WHEN BugSubscriptionFilterTag.include '
                'THEN BugSubscriptionFilterTag.tag END'))==0
        return candidates, Select(BugSubscriptionFilter.id, **select_args)
    else:
        # The bug has some tags.  This will require a bit of fancy
        # footwork. First, though, we will simply want to leave out
        # filters that should only match bugs without tags.
        conditions.append(Not(BugSubscriptionFilter.exclude_any_tags))
        # We're going to have to do a union with another query.  One
        # query will handle filters that are marked to include *any*
        # of the filter's selected tags, and the other query will
        # handle filters that include *all* of the filter's selected
        # tags (as determined by BugSubscriptionFilter.find_all_tags).
        # Every aspect of the unioned queries' WHERE clauses *other
        # than tags* will need to be the same. We could try making a
        # temporary table for the shared results, but that would
        # involve another separate Postgres call, and I think that
        # we've already gotten the big win by separating out the
        # structural subscriptions into "candidates," above.
        #
        # So, up to now we've been assembling the things that are shared
        # between the two queries, but now we start working on the
        # differences between the two unioned queries. "first_select"
        # will hold one set of arguments, and select_args will hold the
        # other.
        first_select = select_args.copy()
        # As mentioned, in this first SELECT we handle filters that
        # match any of the filter's tags.  This can be a relatively
        # straightforward query--we just need a bit more added to
        # our WHERE clause, and we don't need a GROUP BY/HAVING.
        first_select['where'] = And(
            Or(# We want filters that proclaim they simply want any tags.
               BugSubscriptionFilter.include_any_tags,
               # Also include filters that match any tag...
               And(Not(BugSubscriptionFilter.find_all_tags),
                   Or(# ...with a positive match...
                      And(BugSubscriptionFilterTag.include,
                          In(BugSubscriptionFilterTag.tag, tags)),
                      # ...or with a negative match...
                      And(Not(BugSubscriptionFilterTag.include),
                          Not(In(BugSubscriptionFilterTag.tag, tags))),
                      # ...or if the filter does not specify any tags.
                      BugSubscriptionFilterTag.tag == None))),
            *conditions)
        first_select = Select(BugSubscriptionFilter.id, **first_select)
        # We have our first clause.  Now we start on the second one:
        # handling filters that match *all* tags. Our WHERE clause
        # is straightforward and, it should be clear that we are
        # simply focusing on BugSubscriptionFilter.find_all_tags,
        # when the first SELECT did not consider it.
        select_args['where'] = And(
            BugSubscriptionFilter.find_all_tags, *conditions)
        # The GROUP BY collects the filters together.
        select_args['group_by'] = (BugSubscriptionFilter.id,)
        # Now it is time for the HAVING clause, which is where some
        # tricky bits happen. We first make a SQL snippet that
        # represents the tags on this bug.  It is straightforward
        # except for one subtle hack: the addition of the empty
        # space in the array.  This is because we are going to be
        # aggregating the tags on the filters using ARRAY_AGG, which
        # includes NULLs (unlike most other aggregators).  That
        # is an issue here because we use CASE statements to divide
        # up the set of tags that are supposed to be included and
        # supposed to be excluded.  This means that if we aggregate
        # "CASE WHEN BugSubscriptionFilterTag.include THEN
        # BugSubscriptionFilterTag.tag END" then that array will
        # include NULL.  SQL treats NULLs as unknowns that can never
        # be matched, so the array of ['foo', 'bar', NULL] does not
        # contain the array of ['foo', NULL] ("SELECT
        # ARRAY['foo','bar',NULL]::TEXT[] @>
        # ARRAY['foo',NULL]::TEXT[];" is false).  Therefore, so we
        # can make the HAVING statement we want to make without
        # defining a custom Postgres aggregator, we use a single
        # space as, effectively, NULL.  This is safe because a
        # single space is not an acceptable tag.  Again, the
        # clearest alternative is defining a custom Postgres aggregator.
        tags_array = "ARRAY[%s,' ']::TEXT[]" % ",".join(
            quote(tag) for tag in tags)
        # Now comes the HAVING clause itself.
        select_args['having'] = And(
            # The list of tags should be a superset of the filter tags to
            # be included.
            ArrayContains(
                SQL(tags_array),
                # This next line gives us an array of the tags that the
                # filter wants to include.  Notice that it includes the
                # empty string when the condition does not match, per the
                # discussion above.
                ArrayAgg(
                   SQL("CASE WHEN BugSubscriptionFilterTag.include "
                       "THEN BugSubscriptionFilterTag.tag "
                       "ELSE ' '::TEXT END"))),
            # The list of tags should also not intersect with the
            # tags that the filter wants to exclude.
            Not(
                ArrayIntersects(
                    SQL(tags_array),
                    # This next line gives us an array of the tags
                    # that the filter wants to exclude.  We do not bother
                    # with the empty string, and therefore allow NULLs
                    # into the array, because in this case we are
                    # determining whether the sets intersect, not if the
                    # first set subsumes the second.
                    ArrayAgg(
                       SQL('CASE WHEN '
                           'NOT BugSubscriptionFilterTag.include '
                           'THEN BugSubscriptionFilterTag.tag END')))))
        # Everything is ready.  Make our second SELECT statement, UNION
        # it, and return it.
        return candidates, Union(
            first_select,
            Select(
                BugSubscriptionFilter.id,
                **select_args))
