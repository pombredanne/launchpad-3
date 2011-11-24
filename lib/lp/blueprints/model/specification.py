# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = [
    'HasSpecificationsMixin',
    'recursive_blocked_query',
    'recursive_dependent_query',
    'Specification',
    'SpecificationSet',
    ]

from lazr.lifecycle.event import (
    ObjectCreatedEvent,
    ObjectModifiedEvent,
    )
from lazr.lifecycle.objectdelta import ObjectDelta
from sqlobject import (
    BoolCol,
    ForeignKey,
    IntCol,
    SQLMultipleJoin,
    SQLRelatedJoin,
    StringCol,
    )
from storm.locals import (
    Desc,
    SQL,
    )
from storm.store import Store
from zope.component import getUtility
from zope.event import notify
from zope.interface import implements

from canonical.database.constants import (
    DEFAULT,
    UTC_NOW,
    )
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (
    cursor,
    quote,
    SQLBase,
    sqlvalues,
    )
from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from canonical.launchpad.helpers import (
    get_contact_email_addresses,
    )
from lp.app.errors import UserCannotUnsubscribePerson
from lp.blueprints.adapters import SpecificationDelta
from lp.blueprints.enums import (
    NewSpecificationDefinitionStatus,
    SpecificationDefinitionStatus,
    SpecificationFilter,
    SpecificationGoalStatus,
    SpecificationImplementationStatus,
    SpecificationLifecycleStatus,
    SpecificationPriority,
    SpecificationSort,
    )
from lp.blueprints.errors import TargetAlreadyHasSpecification
from lp.blueprints.interfaces.specification import (
    ISpecification,
    ISpecificationSet,
    )
from lp.blueprints.model.specificationbranch import SpecificationBranch
from lp.blueprints.model.specificationbug import SpecificationBug
from lp.blueprints.model.specificationdependency import (
    SpecificationDependency,
    )
from lp.blueprints.model.specificationfeedback import SpecificationFeedback
from lp.blueprints.model.specificationsubscription import (
    SpecificationSubscription,
    )
from lp.bugs.interfaces.buglink import IBugLinkTarget
from lp.bugs.interfaces.bugtask import (
    BugTaskSearchParams,
    IBugTaskSet,
    )
from lp.bugs.interfaces.bugtaskfilter import filter_bugtasks_by_context
from lp.bugs.model.buglinktarget import BugLinkTargetMixin
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.person import validate_public_person
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.product import IProduct
from lp.services.propertycache import (
    cachedproperty,
    get_property_cache,
    )



def recursive_blocked_query(spec):
    return """
        RECURSIVE blocked(id) AS (
            SELECT %s
        UNION
            SELECT sd.specification
            FROM specificationdependency sd, blocked b
            WHERE sd.dependency = b.id
        )""" % spec.id


def recursive_dependent_query(spec):
    return """
        RECURSIVE dependencies(id) AS (
            SELECT %s
        UNION
            SELECT sd.dependency
            FROM specificationdependency sd, dependencies d
            WHERE sd.specification = d.id
        )""" % spec.id


class Specification(SQLBase, BugLinkTargetMixin):
    """See ISpecification."""

    implements(ISpecification, IBugLinkTarget)

    _defaultOrder = ['-priority', 'definition_status', 'name', 'id']

    # db field names
    name = StringCol(unique=True, notNull=True)
    title = StringCol(notNull=True)
    summary = StringCol(notNull=True)
    definition_status = EnumCol(
        schema=SpecificationDefinitionStatus, notNull=True,
        default=SpecificationDefinitionStatus.NEW)
    priority = EnumCol(schema=SpecificationPriority, notNull=True,
        default=SpecificationPriority.UNDEFINED)
    assignee = ForeignKey(dbName='assignee', notNull=False,
        foreignKey='Person',
        storm_validator=validate_public_person, default=None)
    drafter = ForeignKey(dbName='drafter', notNull=False,
        foreignKey='Person',
        storm_validator=validate_public_person, default=None)
    approver = ForeignKey(dbName='approver', notNull=False,
        foreignKey='Person',
        storm_validator=validate_public_person, default=None)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    datecreated = UtcDateTimeCol(notNull=True, default=DEFAULT)
    private = BoolCol(notNull=True, default=False)
    product = ForeignKey(dbName='product', foreignKey='Product',
        notNull=False, default=None)
    productseries = ForeignKey(dbName='productseries',
        foreignKey='ProductSeries', notNull=False, default=None)
    distribution = ForeignKey(dbName='distribution',
        foreignKey='Distribution', notNull=False, default=None)
    distroseries = ForeignKey(dbName='distroseries',
        foreignKey='DistroSeries', notNull=False, default=None)
    goalstatus = EnumCol(schema=SpecificationGoalStatus, notNull=True,
        default=SpecificationGoalStatus.PROPOSED)
    goal_proposer = ForeignKey(dbName='goal_proposer', notNull=False,
        foreignKey='Person',
        storm_validator=validate_public_person, default=None)
    date_goal_proposed = UtcDateTimeCol(notNull=False, default=None)
    goal_decider = ForeignKey(dbName='goal_decider', notNull=False,
        foreignKey='Person',
        storm_validator=validate_public_person, default=None)
    date_goal_decided = UtcDateTimeCol(notNull=False, default=None)
    milestone = ForeignKey(dbName='milestone',
        foreignKey='Milestone', notNull=False, default=None)
    specurl = StringCol(notNull=False, default=None)
    whiteboard = StringCol(notNull=False, default=None)
    direction_approved = BoolCol(notNull=True, default=False)
    man_days = IntCol(notNull=False, default=None)
    implementation_status = EnumCol(
        schema=SpecificationImplementationStatus, notNull=True,
        default=SpecificationImplementationStatus.UNKNOWN)
    superseded_by = ForeignKey(dbName='superseded_by',
        foreignKey='Specification', notNull=False, default=None)
    completer = ForeignKey(dbName='completer', notNull=False,
        foreignKey='Person',
        storm_validator=validate_public_person, default=None)
    date_completed = UtcDateTimeCol(notNull=False, default=None)
    starter = ForeignKey(dbName='starter', notNull=False,
        foreignKey='Person',
        storm_validator=validate_public_person, default=None)
    date_started = UtcDateTimeCol(notNull=False, default=None)

    # useful joins
    _subscriptions = SQLMultipleJoin('SpecificationSubscription',
        joinColumn='specification', orderBy='id')
    subscribers = SQLRelatedJoin('Person',
        joinColumn='specification', otherColumn='person',
        intermediateTable='SpecificationSubscription',
        orderBy=['displayname', 'name'])
    feedbackrequests = SQLMultipleJoin('SpecificationFeedback',
        joinColumn='specification', orderBy='id')
    sprint_links = SQLMultipleJoin('SprintSpecification', orderBy='id',
        joinColumn='specification')
    sprints = SQLRelatedJoin('Sprint', orderBy='name',
        joinColumn='specification', otherColumn='sprint',
        intermediateTable='SprintSpecification')
    bug_links = SQLMultipleJoin(
        'SpecificationBug', joinColumn='specification', orderBy='id')
    bugs = SQLRelatedJoin('Bug',
        joinColumn='specification', otherColumn='bug',
        intermediateTable='SpecificationBug', orderBy='id')
    linked_branches = SQLMultipleJoin('SpecificationBranch',
        joinColumn='specification',
        orderBy='id')
    spec_dependency_links = SQLMultipleJoin('SpecificationDependency',
        joinColumn='specification', orderBy='id')

    dependencies = SQLRelatedJoin('Specification', joinColumn='specification',
        otherColumn='dependency', orderBy='title',
        intermediateTable='SpecificationDependency')
    blocked_specs = SQLRelatedJoin('Specification', joinColumn='dependency',
        otherColumn='specification', orderBy='title',
        intermediateTable='SpecificationDependency')

    @cachedproperty
    def subscriptions(self):
        """Sort the subscriptions"""
        from lp.registry.model.person import person_sort_key
        return sorted(
            self._subscriptions, key=lambda sub: person_sort_key(sub.person))

    @property
    def target(self):
        """See ISpecification."""
        if self.product:
            return self.product
        return self.distribution

    def setTarget(self, target):
        """See ISpecification."""
        if IProduct.providedBy(target):
            self.product = target
            self.distribution = None
        elif IDistribution.providedBy(target):
            self.product = None
            self.distribution = target
        else:
            raise AssertionError("Unknown target: %s" % target)

    def retarget(self, target):
        """See ISpecification."""
        if self.target == target:
            return

        self.validateMove(target)

        # We must lose any goal we have set and approved/declined because we
        # are moving to a different target that will have different
        # policies and drivers.
        self.productseries = None
        self.distroseries = None
        self.goalstatus = SpecificationGoalStatus.PROPOSED
        self.goal_proposer = None
        self.date_goal_proposed = None
        self.milestone = None

        self.setTarget(target)
        self.priority = SpecificationPriority.UNDEFINED
        self.direction_approved = False

    def validateMove(self, target):
        """See ISpecification."""
        if target.getSpecification(self.name) is not None:
            raise TargetAlreadyHasSpecification(target, self.name)

    @property
    def goal(self):
        """See ISpecification."""
        if self.productseries:
            return self.productseries
        return self.distroseries

    def proposeGoal(self, goal, proposer):
        """See ISpecification."""
        if goal is None:
            # we are clearing goals
            self.productseries = None
            self.distroseries = None
        elif IProductSeries.providedBy(goal):
            # set the product series as a goal
            self.productseries = goal
            self.goal_proposer = proposer
            self.date_goal_proposed = UTC_NOW
            # and make sure there is no leftover distroseries goal
            self.distroseries = None
        elif IDistroSeries.providedBy(goal):
            # set the distroseries goal
            self.distroseries = goal
            self.goal_proposer = proposer
            self.date_goal_proposed = UTC_NOW
            # and make sure there is no leftover distroseries goal
            self.productseries = None
        else:
            raise AssertionError('Inappropriate goal.')
        # record who made the proposal, and when
        self.goal_proposer = proposer
        self.date_goal_proposed = UTC_NOW
        # and of course set the goal status to PROPOSED
        self.goalstatus = SpecificationGoalStatus.PROPOSED
        # the goal should now also not have a decider
        self.goal_decider = None
        self.date_goal_decided = None
        if goal is not None and goal.personHasDriverRights(proposer):
            self.acceptBy(proposer)

    def acceptBy(self, decider):
        """See ISpecification."""
        self.goalstatus = SpecificationGoalStatus.ACCEPTED
        self.goal_decider = decider
        self.date_goal_decided = UTC_NOW

    def declineBy(self, decider):
        """See ISpecification."""
        self.goalstatus = SpecificationGoalStatus.DECLINED
        self.goal_decider = decider
        self.date_goal_decided = UTC_NOW

    def getSprintSpecification(self, sprintname):
        """See ISpecification."""
        for sprintspecification in self.sprint_links:
            if sprintspecification.sprint.name == sprintname:
                return sprintspecification
        return None

    def getFeedbackRequests(self, person):
        """See ISpecification."""
        fb = SpecificationFeedback.selectBy(
            specification=self, reviewer=person)
        return fb.prejoin(['requester'])

    def notificationRecipientAddresses(self):
        """See ISpecification."""
        related_people = [
            self.owner, self.assignee, self.approver, self.drafter]
        related_people = [
            person for person in related_people if person is not None]
        subscribers = [
            subscription.person for subscription in self.subscriptions]
        addresses = set()
        for person in related_people + subscribers:
            addresses.update(get_contact_email_addresses(person))
        return sorted(addresses)

    # emergent properties
    @property
    def is_incomplete(self):
        """See ISpecification."""
        return not self.is_complete

    # Several other classes need to generate lists of specifications, and
    # one thing they often have to filter for is completeness. We maintain
    # this single canonical query string here so that it does not have to be
    # cargo culted into Product, Distribution, ProductSeries etc

    # Also note that there is a constraint in the database which ensures
    # that date_completed is set if the spec is complete, and that db
    # constraint parrots this definition exactly.

    # NB NB NB if you change this definition PLEASE update the db constraint
    # Specification.specification_completion_recorded_chk !!!
    completeness_clause = ("""
        Specification.implementation_status = %s OR
        Specification.definition_status IN ( %s, %s ) OR
        (Specification.implementation_status = %s AND
         Specification.definition_status = %s)
        """ % sqlvalues(SpecificationImplementationStatus.IMPLEMENTED.value,
                        SpecificationDefinitionStatus.OBSOLETE.value,
                        SpecificationDefinitionStatus.SUPERSEDED.value,
                        SpecificationImplementationStatus.INFORMATIONAL.value,
                        SpecificationDefinitionStatus.APPROVED.value))

    @property
    def is_complete(self):
        """See `ISpecification`."""
        # Implemented blueprints are by definition complete.
        if (self.implementation_status ==
            SpecificationImplementationStatus.IMPLEMENTED):
            return True
        # Obsolete and superseded blueprints are considered complete.
        if self.definition_status in (
            SpecificationDefinitionStatus.OBSOLETE,
            SpecificationDefinitionStatus.SUPERSEDED):
            return True
        # Approved information blueprints are also considered complete.
        if ((self.implementation_status ==
             SpecificationImplementationStatus.INFORMATIONAL) and
            (self.definition_status ==
             SpecificationDefinitionStatus.APPROVED)):
            return True
        else:
            return False

    # NB NB If you change this definition, please update the equivalent
    # DB constraint Specification.specification_start_recorded_chk
    # We choose to define "started" as the set of delivery states NOT
    # in the values we select. Another option would be to say "anything less
    # than a threshold" and to comment the dbschema that "anything not
    # started should be less than the threshold". We'll see how maintainable
    # this is.
    started_clause = """
        Specification.implementation_status NOT IN (%s, %s, %s, %s) OR
        (Specification.implementation_status = %s AND
         Specification.definition_status = %s)
        """ % sqlvalues(SpecificationImplementationStatus.UNKNOWN.value,
                        SpecificationImplementationStatus.NOTSTARTED.value,
                        SpecificationImplementationStatus.DEFERRED.value,
                        SpecificationImplementationStatus.INFORMATIONAL.value,
                        SpecificationImplementationStatus.INFORMATIONAL.value,
                        SpecificationDefinitionStatus.APPROVED.value)

    @property
    def is_started(self):
        """See ISpecification. This is a code implementation of the
        SQL in self.started_clause
        """
        return (self.implementation_status not in [
                    SpecificationImplementationStatus.UNKNOWN,
                    SpecificationImplementationStatus.NOTSTARTED,
                    SpecificationImplementationStatus.DEFERRED,
                    SpecificationImplementationStatus.INFORMATIONAL,
                    ]
                or ((self.implementation_status ==
                     SpecificationImplementationStatus.INFORMATIONAL) and
                    (self.definition_status ==
                     SpecificationDefinitionStatus.APPROVED)))

    @property
    def lifecycle_status(self):
        """Combine the is_complete and is_started emergent properties."""
        if self.is_complete:
            return SpecificationLifecycleStatus.COMPLETE
        elif self.is_started:
            return SpecificationLifecycleStatus.STARTED
        else:
            return SpecificationLifecycleStatus.NOTSTARTED

    def setDefinitionStatus(self, definition_status, user):
        self.definition_status = definition_status
        self.updateLifecycleStatus(user)

    def setImplementationStatus(self, implementation_status, user):
        self.implementation_status = implementation_status
        self.updateLifecycleStatus(user)

    def updateLifecycleStatus(self, user):
        """See ISpecification."""
        newstatus = None
        if self.is_started:
            if self.starterID is None:
                newstatus = SpecificationLifecycleStatus.STARTED
                self.date_started = UTC_NOW
                self.starter = user
        else:
            if self.starterID is not None:
                newstatus = SpecificationLifecycleStatus.NOTSTARTED
                self.date_started = None
                self.starter = None
        if self.is_complete:
            if self.completerID is None:
                newstatus = SpecificationLifecycleStatus.COMPLETE
                self.date_completed = UTC_NOW
                self.completer = user
        else:
            if self.completerID is not None:
                self.date_completed = None
                self.completer = None
                if self.is_started:
                    newstatus = SpecificationLifecycleStatus.STARTED
                else:
                    newstatus = SpecificationLifecycleStatus.NOTSTARTED

        return newstatus

    @property
    def is_blocked(self):
        """See ISpecification."""
        for spec in self.dependencies:
            if spec.is_incomplete:
                return True
        return False

    @property
    def has_accepted_goal(self):
        """See ISpecification."""
        if (self.goal is not None and
            self.goalstatus == SpecificationGoalStatus.ACCEPTED):
            return True
        return False

    def getDelta(self, old_spec, user):
        """See ISpecification."""
        delta = ObjectDelta(old_spec, self)
        delta.recordNewValues(("title", "summary",
                               "specurl", "productseries",
                               "distroseries", "milestone"))
        delta.recordNewAndOld(("name", "priority", "definition_status",
                               "target", "approver", "assignee", "drafter",
                               "whiteboard"))
        delta.recordListAddedAndRemoved("bugs",
                                        "bugs_linked",
                                        "bugs_unlinked")

        if delta.changes:
            changes = delta.changes
            changes["specification"] = self
            changes["user"] = user

            return SpecificationDelta(**changes)
        else:
            return None

    @property
    def informational(self):
        """For backwards compatibility:
        implemented as a value in implementation_status.
        """
        return (self.implementation_status ==
                SpecificationImplementationStatus.INFORMATIONAL)

    # subscriptions
    def subscription(self, person):
        """See ISpecification."""
        return SpecificationSubscription.selectOneBy(
                specification=self, person=person)

    def getSubscriptionByName(self, name):
        """See ISpecification."""
        for sub in self.subscriptions:
            if sub.person.name == name:
                return sub
        return None

    def subscribe(self, person, subscribed_by=None, essential=False):
        """See ISpecification."""
        if subscribed_by is None:
            subscribed_by = person
        # Create or modify a user's subscription to this blueprint.
        # First see if a relevant subscription exists, and if so, return it
        sub = self.subscription(person)
        if sub is not None:
            if sub.essential != essential:
                # If a subscription already exists, but the value for
                # 'essential' changes, there's no need to create a new
                # subscription, but we modify the existing subscription
                # and notify the user about the change.
                sub.essential = essential
                # The second argument should really be a copy of sub with
                # only the essential attribute changed, but we know
                # that we can get away with not examining the attribute
                # at all - it's a boolean!
                notify(ObjectModifiedEvent(
                        sub, sub, ['essential'], user=subscribed_by))
            return sub
        # since no previous subscription existed, create and return a new one
        sub = SpecificationSubscription(specification=self,
            person=person, essential=essential)
        property_cache = get_property_cache(self)
        if 'subscription' in property_cache:
            from lp.registry.model.person import person_sort_key
            property_cache.subscriptions.append(sub)
            property_cache.subscriptions.sort(
                key=lambda sub: person_sort_key(sub.person))
        notify(ObjectCreatedEvent(sub, user=subscribed_by))
        return sub

    def unsubscribe(self, person, unsubscribed_by):
        """See ISpecification."""
        # see if a relevant subscription exists, and if so, delete it
        if person is None:
            person = unsubscribed_by
        for sub in self.subscriptions:
            if sub.person.id == person.id:
                if not sub.canBeUnsubscribedByUser(unsubscribed_by):
                    raise UserCannotUnsubscribePerson(
                        '%s does not have permission to unsubscribe %s.' % (
                            unsubscribed_by.displayname,
                            person.displayname))
                get_property_cache(self).subscriptions.remove(sub)
                SpecificationSubscription.delete(sub.id)
                return

    def isSubscribed(self, person):
        """See lp.blueprints.interfaces.specification.ISpecification."""
        if person is None:
            return False

        return bool(self.subscription(person))

    # queueing
    def queue(self, reviewer, requester, queuemsg=None):
        """See ISpecification."""
        for fbreq in self.feedbackrequests:
            if (fbreq.reviewer.id == reviewer.id and
                fbreq.requester == requester.id):
                # we have a relevant request already, update it
                fbreq.queuemsg = queuemsg
                return fbreq
        # since no previous feedback request existed for this person,
        # create a new one
        return SpecificationFeedback(
            specification=self,
            reviewer=reviewer,
            requester=requester,
            queuemsg=queuemsg)

    def unqueue(self, reviewer, requester):
        """See ISpecification."""
        # see if a relevant queue entry exists, and if so, delete it
        for fbreq in self.feedbackrequests:
            if (fbreq.reviewer.id == reviewer.id and
                fbreq.requester.id == requester.id):
                SpecificationFeedback.delete(fbreq.id)
                return

    # Template methods for BugLinkTargetMixin
    buglinkClass = SpecificationBug

    def createBugLink(self, bug):
        """See BugLinkTargetMixin."""
        return SpecificationBug(specification=self, bug=bug)

    # sprint linking
    def linkSprint(self, sprint, user):
        """See ISpecification."""
        from lp.blueprints.model.sprintspecification import (
            SprintSpecification)
        for sprint_link in self.sprint_links:
            # sprints have unique names
            if sprint_link.sprint.name == sprint.name:
                return sprint_link
        sprint_link = SprintSpecification(specification=self,
            sprint=sprint, registrant=user)
        if sprint.isDriver(user):
            sprint_link.acceptBy(user)
        return sprint_link

    def unlinkSprint(self, sprint):
        """See ISpecification."""
        from lp.blueprints.model.sprintspecification import (
            SprintSpecification)
        for sprint_link in self.sprint_links:
            # sprints have unique names
            if sprint_link.sprint.name == sprint.name:
                SprintSpecification.delete(sprint_link.id)
                return sprint_link

    # dependencies
    def createDependency(self, specification):
        """See ISpecification."""
        for deplink in self.spec_dependency_links:
            if deplink.dependency.id == specification.id:
                return deplink
        return SpecificationDependency(specification=self,
            dependency=specification)

    def removeDependency(self, specification):
        """See ISpecification."""
        # see if a relevant dependency link exists, and if so, delete it
        for deplink in self.spec_dependency_links:
            if deplink.dependency.id == specification.id:
                SpecificationDependency.delete(deplink.id)
                return deplink

    @property
    def all_deps(self):
        return Store.of(self).with_(
            SQL(recursive_dependent_query(self))).find(
            Specification,
            Specification.id != self.id,
            SQL('Specification.id in (select id from dependencies)')
            ).order_by(Specification.name, Specification.id)

    @property
    def all_blocked(self):
        """See `ISpecification`."""
        return Store.of(self).with_(
            SQL(recursive_blocked_query(self))).find(
            Specification,
            Specification.id != self.id,
            SQL('Specification.id in (select id from blocked)')
            ).order_by(Specification.name, Specification.id)

    # branches
    def getBranchLink(self, branch):
        return SpecificationBranch.selectOneBy(
            specificationID=self.id, branchID=branch.id)

    def linkBranch(self, branch, registrant):
        branch_link = self.getBranchLink(branch)
        if branch_link is not None:
            return branch_link
        branch_link = SpecificationBranch(
            specification=self, branch=branch, registrant=registrant)
        notify(ObjectCreatedEvent(branch_link))
        return branch_link

    def unlinkBranch(self, branch, user):
        spec_branch = self.getBranchLink(branch)
        spec_branch.destroySelf()

    def getLinkedBugTasks(self, user):
        """See `ISpecification`."""
        params = BugTaskSearchParams(user=user, linked_blueprints=self.id)
        tasks = getUtility(IBugTaskSet).search(params)
        if self.distroseries is not None:
            context = self.distroseries
        elif self.distribution is not None:
            context = self.distribution
        elif self.productseries is not None:
            context = self.productseries
        else:
            context = self.product
        return filter_bugtasks_by_context(context, tasks)

    def __repr__(self):
        return '<Specification %s %r for %r>' % (
            self.id, self.name, self.target.name)


class HasSpecificationsMixin:
    """A mixin class that implements many of the common shortcut properties
    for other classes that have specifications.
    """

    def specifications(self, sort=None, quantity=None, filter=None,
                       prejoin_people=True):
        """See IHasSpecifications."""
        # this should be implemented by the actual context class
        raise NotImplementedError

    def _specification_sort(self, sort):
        """Return the storm sort order for 'specifications'.

        :param sort: As per HasSpecificationsMixin.specifications.
        """
        # sort by priority descending, by default
        if sort is None or sort == SpecificationSort.PRIORITY:
            return (
                Desc(Specification.priority), Specification.definition_status,
                Specification.name)
        elif sort == SpecificationSort.DATE:
            return (Desc(Specification.datecreated), Specification.id)

    def _preload_specifications_people(self, query):
        """Perform eager loading of people and their validity for query.

        :param query: a string query generated in the 'specifications'
            method.
        :return: A DecoratedResultSet with Person precaching setup.
        """
        # Circular import.
        from lp.registry.model.person import Person

        def cache_people(rows):
            # Find the people we need:
            person_ids = set()
            for spec in rows:
                person_ids.add(spec.assigneeID)
                person_ids.add(spec.approverID)
                person_ids.add(spec.drafterID)
            person_ids.discard(None)
            if not person_ids:
                return
            # Query those people
            origin = [Person]
            columns = [Person]
            validity_info = Person._validity_queries()
            origin.extend(validity_info["joins"])
            columns.extend(validity_info["tables"])
            decorators = validity_info["decorators"]
            personset = Store.of(self).using(*origin).find(
                tuple(columns),
                Person.id.is_in(person_ids),
                )
            for row in personset:
                person = row[0]
                index = 1
                for decorator in decorators:
                    column = row[index]
                    index += 1
                    decorator(person, column)

        results = Store.of(self).find(
            Specification,
            SQL(query),
            )
        return DecoratedResultSet(results, pre_iter_hook=cache_people)

    @property
    def valid_specifications(self):
        """See IHasSpecifications."""
        return self.specifications(filter=[SpecificationFilter.VALID])

    @property
    def latest_specifications(self):
        """See IHasSpecifications."""
        return self.specifications(sort=SpecificationSort.DATE, quantity=5)

    @property
    def latest_completed_specifications(self):
        """See IHasSpecifications."""
        return self.specifications(sort=SpecificationSort.DATE, quantity=5,
            filter=[SpecificationFilter.COMPLETE, ])

    @property
    def specification_count(self):
        """See IHasSpecifications."""
        return self.specifications(filter=[SpecificationFilter.ALL]).count()


class SpecificationSet(HasSpecificationsMixin):
    """The set of feature specifications."""

    implements(ISpecificationSet)

    def __init__(self):
        """See ISpecificationSet."""
        self.title = 'Specifications registered in Launchpad'
        self.displayname = 'All Specifications'

    def getStatusCountsForProductSeries(self, product_series):
        """See `ISpecificationSet`."""
        cur = cursor()
        condition = """
            (Specification.productseries = %s
                 OR Milestone.productseries = %s)
            """ % sqlvalues(product_series, product_series)
        query = """
            SELECT Specification.implementation_status, count(*)
            FROM Specification
                LEFT JOIN Milestone ON Specification.milestone = Milestone.id
            WHERE
                %s
            GROUP BY Specification.implementation_status
            """ % condition
        cur.execute(query)
        return cur.fetchall()

    @property
    def all_specifications(self):
        return Specification.select()

    def __iter__(self):
        """See ISpecificationSet."""
        return iter(self.all_specifications)

    @property
    def has_any_specifications(self):
        return self.all_specifications.count() != 0

    def specifications(self, sort=None, quantity=None, filter=None,
                       prejoin_people=True):
        """See IHasSpecifications."""

        # Make a new list of the filter, so that we do not mutate what we
        # were passed as a filter
        if not filter:
            # When filter is None or [] then we decide the default
            # which for a product is to show incomplete specs
            filter = [SpecificationFilter.INCOMPLETE]

        # now look at the filter and fill in the unsaid bits

        # defaults for completeness: if nothing is said about completeness
        # then we want to show INCOMPLETE
        completeness = False
        for option in [
            SpecificationFilter.COMPLETE,
            SpecificationFilter.INCOMPLETE]:
            if option in filter:
                completeness = True
        if completeness is False:
            filter.append(SpecificationFilter.INCOMPLETE)

        # defaults for acceptance: in this case we have nothing to do
        # because specs are not accepted/declined against a distro

        # defaults for informationalness: we don't have to do anything
        # because the default if nothing is said is ANY

        # sort by priority descending, by default
        if sort is None or sort == SpecificationSort.PRIORITY:
            order = ['-priority', 'Specification.definition_status',
                     'Specification.name']
        elif sort == SpecificationSort.DATE:
            if SpecificationFilter.COMPLETE in filter:
                # if we are showing completed, we care about date completed
                order = ['-Specification.date_completed', 'Specification.id']
            else:
                # if not specially looking for complete, we care about date
                # registered
                order = ['-Specification.datecreated', 'Specification.id']

        # figure out what set of specifications we are interested in. for
        # products, we need to be able to filter on the basis of:
        #
        #  - completeness.
        #  - informational.
        #

        # filter out specs on inactive products
        base = """(Specification.product IS NULL OR
                   Specification.product NOT IN
                    (SELECT Product.id FROM Product
                     WHERE Product.active IS FALSE))
                """
        query = base
        # look for informational specs
        if SpecificationFilter.INFORMATIONAL in filter:
            query += (' AND Specification.implementation_status = %s ' %
                quote(SpecificationImplementationStatus.INFORMATIONAL.value))

        # filter based on completion. see the implementation of
        # Specification.is_complete() for more details
        completeness = Specification.completeness_clause

        if SpecificationFilter.COMPLETE in filter:
            query += ' AND ( %s ) ' % completeness
        elif SpecificationFilter.INCOMPLETE in filter:
            query += ' AND NOT ( %s ) ' % completeness

        # Filter for validity. If we want valid specs only then we should
        # exclude all OBSOLETE or SUPERSEDED specs
        if SpecificationFilter.VALID in filter:
            # XXX: kiko 2007-02-07: this is untested and was broken.
            query += (
                ' AND Specification.definition_status NOT IN ( %s, %s ) ' %
                sqlvalues(SpecificationDefinitionStatus.OBSOLETE,
                          SpecificationDefinitionStatus.SUPERSEDED))

        # ALL is the trump card
        if SpecificationFilter.ALL in filter:
            query = base

        # Filter for specification text
        for constraint in filter:
            if isinstance(constraint, basestring):
                # a string in the filter is a text search filter
                query += ' AND Specification.fti @@ ftq(%s) ' % quote(
                    constraint)

        results = Specification.select(query, orderBy=order, limit=quantity)
        if prejoin_people:
            results = results.prejoin(['assignee', 'approver', 'drafter'])
        return results

    def getByURL(self, url):
        """See ISpecificationSet."""
        specification = Specification.selectOneBy(specurl=url)
        if specification is None:
            return None
        return specification

    @property
    def coming_sprints(self):
        """See ISpecificationSet."""
        from lp.blueprints.model.sprint import Sprint
        return Sprint.select("time_ends > 'NOW'", orderBy='time_starts',
            limit=5)

    def new(self, name, title, specurl, summary, definition_status,
        owner, approver=None, product=None, distribution=None, assignee=None,
        drafter=None, whiteboard=None,
        priority=SpecificationPriority.UNDEFINED):
        """See ISpecificationSet."""
        # Adapt the NewSpecificationDefinitionStatus item to a
        # SpecificationDefinitionStatus item.
        status_name = definition_status.name
        status_names = NewSpecificationDefinitionStatus.items.mapping.keys()
        if status_name not in status_names:
            raise AssertionError(
                "definition_status must an item found in "
                "NewSpecificationDefinitionStatus.")
        definition_status = SpecificationDefinitionStatus.items[status_name]
        return Specification(name=name, title=title, specurl=specurl,
            summary=summary, priority=priority,
            definition_status=definition_status, owner=owner,
            approver=approver, product=product, distribution=distribution,
            assignee=assignee, drafter=drafter, whiteboard=whiteboard)

    def getDependencyDict(self, specifications):
        """See `ISpecificationSet`."""
        specification_ids = [spec.id for spec in specifications]

        if len(specification_ids) == 0:
            return {}

        results = Store.of(specifications[0]).execute("""
            SELECT SpecificationDependency.specification,
                   SpecificationDependency.dependency
            FROM SpecificationDependency, Specification
            WHERE SpecificationDependency.specification IN %s
            AND SpecificationDependency.dependency = Specification.id
            ORDER BY Specification.priority DESC, Specification.name,
                     Specification.id
        """ % sqlvalues(specification_ids)).get_all()

        dependencies = {}
        for spec_id, dep_id in results:
            if spec_id not in dependencies:
                dependencies[spec_id] = []
            dependency = Specification.get(dep_id)
            dependencies[spec_id].append(dependency)

        return dependencies

    def get(self, spec_id):
        """See lp.blueprints.interfaces.specification.ISpecificationSet."""
        return Specification.get(spec_id)
