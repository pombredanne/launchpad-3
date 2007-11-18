# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = [
    'HasSpecificationsMixin',
    'Specification',
    'SpecificationSet',
    ]

from zope.interface import implements
from zope.event import notify

from sqlobject import (
    ForeignKey, IntCol, StringCol, SQLMultipleJoin, SQLRelatedJoin, BoolCol)

from canonical.launchpad.interfaces import (
    IBugLinkTarget,
    IDistroSeries,
    IProductSeries,
    ISpecification,
    ISpecificationSet,
    SpecificationDefinitionStatus,
    SpecificationFilter,
    SpecificationGoalStatus,
    SpecificationImplementationStatus,
    SpecificationLifecycleStatus,
    SpecificationPriority,
    SpecificationSort,
    )

from canonical.database.sqlbase import SQLBase, quote, sqlvalues
from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol

from canonical.launchpad.helpers import (
    contactEmailAddresses, shortlist)

from canonical.launchpad.event.sqlobjectevent import (
    SQLObjectCreatedEvent, SQLObjectDeletedEvent, SQLObjectModifiedEvent)

from canonical.launchpad.database.buglinktarget import BugLinkTargetMixin
from canonical.launchpad.database.mentoringoffer import MentoringOffer
from canonical.launchpad.database.specificationdependency import (
    SpecificationDependency)
from canonical.launchpad.database.specificationbranch import (
    SpecificationBranch)
from canonical.launchpad.database.specificationbug import (
    SpecificationBug)
from canonical.launchpad.database.specificationfeedback import (
    SpecificationFeedback)
from canonical.launchpad.database.specificationsubscription import (
    SpecificationSubscription)
from canonical.launchpad.database.sprintspecification import (
    SprintSpecification)
from canonical.launchpad.database.sprint import Sprint

from canonical.launchpad.components import ObjectDelta
from canonical.launchpad.components.specification import SpecificationDelta


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
        foreignKey='Person', default=None)
    drafter = ForeignKey(dbName='drafter', notNull=False,
        foreignKey='Person', default=None)
    approver = ForeignKey(dbName='approver', notNull=False,
        foreignKey='Person', default=None)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    datecreated = UtcDateTimeCol(notNull=True, default=DEFAULT)
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
        foreignKey='Person', default=None)
    date_goal_proposed = UtcDateTimeCol(notNull=False, default=None)
    goal_decider = ForeignKey(dbName='goal_decider', notNull=False,
        foreignKey='Person', default=None)
    date_goal_decided = UtcDateTimeCol(notNull=False, default=None)
    milestone = ForeignKey(dbName='milestone',
        foreignKey='Milestone', notNull=False, default=None)
    specurl = StringCol(notNull=True)
    whiteboard = StringCol(notNull=False, default=None)
    direction_approved = BoolCol(notNull=True, default=False)
    man_days = IntCol(notNull=False, default=None)
    implementation_status = EnumCol(
        schema=SpecificationImplementationStatus, notNull=True,
        default=SpecificationImplementationStatus.UNKNOWN)
    superseded_by = ForeignKey(dbName='superseded_by',
        foreignKey='Specification', notNull=False, default=None)
    completer = ForeignKey(dbName='completer', notNull=False,
        foreignKey='Person', default=None)
    date_completed = UtcDateTimeCol(notNull=False, default=None)
    starter = ForeignKey(dbName='starter', notNull=False,
        foreignKey='Person', default=None)
    date_started = UtcDateTimeCol(notNull=False, default=None)

    # useful joins
    mentoring_offers = SQLMultipleJoin(
            'MentoringOffer', joinColumn='specification', orderBy='id')
    subscriptions = SQLMultipleJoin('SpecificationSubscription',
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
    bug_links = SQLMultipleJoin('SpecificationBug', joinColumn='specification',
        orderBy='id')
    bugs = SQLRelatedJoin('Bug',
        joinColumn='specification', otherColumn='bug',
        intermediateTable='SpecificationBug', orderBy='id')
    branch_links = SQLMultipleJoin('SpecificationBranch',
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

    # attributes
    @property
    def target(self):
        """See ISpecification."""
        if self.product:
            return self.product
        return self.distribution

    def retarget(self, product=None, distribution=None):
        """See ISpecification."""
        assert not (product and distribution)
        assert (product or distribution)

        # we need to ensure that there is not already a spec with this name
        # for this new target
        if product:
            assert product.getSpecification(self.name) is None
        elif distribution:
            assert distribution.getSpecification(self.name) is None

        # if we are not changing anything, then return
        if self.product == product and self.distribution == distribution:
            return

        # we must lose any goal we have set and approved/declined because we
        # are moving to a different product that will have different
        # policies and drivers
        self.productseries = None
        self.distroseries = None
        self.goalstatus = SpecificationGoalStatus.PROPOSED
        self.goal_proposer = None
        self.date_goal_proposed = None
        self.milestone = None

        # set the new values
        self.product = product
        self.distribution = distribution
        self.priority = SpecificationPriority.UNDEFINED
        self.direction_approved = False

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
            raise AssertionError, 'Inappropriate goal.'
        # record who made the proposal, and when
        self.goal_proposer = proposer
        self.date_goal_proposed = UTC_NOW
        # and of course set the goal status to PROPOSED
        self.goalstatus = SpecificationGoalStatus.PROPOSED
        # the goal should now also not have a decider
        self.goal_decider = None
        self.date_goal_decided = None

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
        reqlist = []
        for fbreq in self.feedbackrequests:
            if fbreq.reviewer.id == person.id:
                reqlist.append(fbreq)
        return reqlist

    def canMentor(self, user):
        """See ICanBeMentored."""
        return not (not user or
                    self.isMentor(user) or
                    self.is_complete or
                    not user.teams_participated_in)

    def isMentor(self, user):
        """See ICanBeMentored."""
        return MentoringOffer.selectOneBy(
            specification=self, owner=user) is not None

    def offerMentoring(self, user, team):
        """See ICanBeMentored."""
        # if an offer exists, then update the team
        mentoringoffer = MentoringOffer.selectOneBy(
            specification=self, owner=user)
        if mentoringoffer is not None:
            mentoringoffer.team = team
            return mentoringoffer
        # if no offer exists, create one from scratch
        mentoringoffer = MentoringOffer(owner=user, team=team,
            specification=self)
        notify(SQLObjectCreatedEvent(mentoringoffer, user=user))
        return mentoringoffer

    def retractMentoring(self, user):
        """See ICanBeMentored."""
        mentoringoffer = MentoringOffer.selectOneBy(
            specification=self, owner=user)
        if mentoringoffer is not None:
            notify(SQLObjectDeletedEvent(mentoringoffer, user=user))
            MentoringOffer.delete(mentoringoffer.id)

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
            addresses.update(contactEmailAddresses(person))
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
    completeness_clause =  ("""
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
    started_clause =  """
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


    def updateLifecycleStatus(self, user):
        """See ISpecification."""
        newstatus = None
        if self.is_started:
            if self.starter is None:
                newstatus = SpecificationLifecycleStatus.STARTED
                self.date_started = UTC_NOW
                self.starter = user
        else:
            if self.starter is not None:
                newstatus = SpecificationLifecycleStatus.NOTSTARTED
                self.date_started = None
                self.starter = None
        if self.is_complete:
            if self.completer is None:
                newstatus = SpecificationLifecycleStatus.COMPLETE
                self.date_completed = UTC_NOW
                self.completer = user
        else:
            if self.completer is not None:
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
        delta.recordNewValues(("title", "summary", "whiteboard",
                               "specurl", "productseries",
                               "distroseries", "milestone"))
        delta.recordNewAndOld(("name", "priority", "definition_status", "target",
                               "approver", "assignee", "drafter"))
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

    def subscribe(self, person, user, essential):
        """Create or modify a user's subscription to this blueprint."""
        # first see if a relevant subscription exists, and if so, return it
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
                notify(
                    SQLObjectModifiedEvent(sub, sub, ['essential'], user=user))
            return sub
        # since no previous subscription existed, create and return a new one
        sub = SpecificationSubscription(specification=self,
            person=person, essential=essential)
        notify(SQLObjectCreatedEvent(sub, user=user))
        return sub

    def unsubscribe(self, person):
        """See ISpecification."""
        # see if a relevant subscription exists, and if so, delete it
        for sub in self.subscriptions:
            if sub.person.id == person.id:
                SpecificationSubscription.delete(sub.id)
                return

    def isSubscribed(self, person):
        """See canonical.launchpad.interfaces.ISpecification."""
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

    def _find_all_deps(self, deps):
        """This adds all dependencies of this spec (and their deps) to
        deps.

        The function is called recursively, as part of self.all_deps.
        """
        for dep in self.dependencies:
            if dep not in deps:
                deps.add(dep)
                dep._find_all_deps(deps)

    @property
    def all_deps(self):
        deps = set()
        self._find_all_deps(deps)
        return sorted(shortlist(deps),
                    key=lambda s: (s.definition_status, s.priority, s.title))

    def _find_all_blocked(self, blocked):
        """This adds all blockers of this spec (and their blockers) to
        blocked.

        The function is called recursively, as part of self.all_blocked.
        """
        for blocker in self.blocked_specs:
            if blocker not in blocked:
                blocked.add(blocker)
                blocker._find_all_blocked(blocked)

    @property
    def all_blocked(self):
        blocked = set()
        self._find_all_blocked(blocked)
        return sorted(blocked, key=lambda s: (s.definition_status, s.priority, s.title))

    # branches
    def getBranchLink(self, branch):
        return SpecificationBranch.selectOneBy(
            specificationID=self.id, branchID=branch.id)

    def linkBranch(self, branch, registrant, summary=None):
        branchlink = self.getBranchLink(branch)
        if branchlink is not None:
            return branchlink
        branch.date_last_modified = UTC_NOW
        return SpecificationBranch(specification=self,
                                   branch=branch,
                                   summary=summary,
                                   registrant=registrant)


class HasSpecificationsMixin:
    """A mixin class that implements many of the common shortcut properties
    for other classes that have specifications.
    """

    def specifications(self, sort=None, quantity=None, filter=None):
        """See IHasSpecifications."""
        # this should be implemented by the actual context class
        raise NotImplementedError

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
            filter=[SpecificationFilter.COMPLETE,])

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

    def __iter__(self):
        """See ISpecificationSet."""
        for row in Specification.select():
            yield row

    def specifications(self, sort=None, quantity=None, filter=None):
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
            order = ['-priority', 'Specification.definition_status', 'Specification.name']
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
        completeness =  Specification.completeness_clause

        if SpecificationFilter.COMPLETE in filter:
            query += ' AND ( %s ) ' % completeness
        elif SpecificationFilter.INCOMPLETE in filter:
            query += ' AND NOT ( %s ) ' % completeness

        # Filter for validity. If we want valid specs only then we should
        # exclude all OBSOLETE or SUPERSEDED specs
        if SpecificationFilter.VALID in filter:
            # XXX: this is untested and was broken. -- kiko 2007-02-07
            query += (' AND Specification.definition_status NOT IN ( %s, %s ) ' %
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

        # now do the query, and remember to prejoin to people
        results = Specification.select(query, orderBy=order, limit=quantity)
        return results.prejoin(['assignee', 'approver', 'drafter'])

    def getByURL(self, url):
        """See ISpecificationSet."""
        specification = Specification.selectOneBy(specurl=url)
        if specification is None:
            return None
        return specification

    @property
    def coming_sprints(self):
        """See ISpecificationSet."""
        return Sprint.select("time_ends > 'NOW'", orderBy='time_starts',
            limit=5)

    def new(self, name, title, specurl, summary, definition_status,
        owner, approver=None, product=None, distribution=None, assignee=None,
        drafter=None, whiteboard=None,
        priority=SpecificationPriority.UNDEFINED):
        """See ISpecificationSet."""
        return Specification(name=name, title=title, specurl=specurl,
            summary=summary, priority=priority,
            definition_status=definition_status, owner=owner,
            approver=approver, product=product, distribution=distribution,
            assignee=assignee, drafter=drafter, whiteboard=whiteboard)

