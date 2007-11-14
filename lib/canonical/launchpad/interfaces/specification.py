# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Specification interfaces."""

__metaclass__ = type

__all__ = [
    'INewSpecification',
    'INewSpecificationSeriesGoal',
    'INewSpecificationSprint',
    'INewSpecificationTarget',
    'INewSpecificationProjectTarget',
    'ISpecification',
    'ISpecificationSet',
    'ISpecificationDelta',
    'SpecificationDefinitionStatus',
    'SpecificationFilter',
    'SpecificationGoalStatus',
    'SpecificationImplementationStatus',
    'SpecificationLifecycleStatus',
    'SpecificationPriority',
    'SpecificationSort'
    ]


from zope.interface import Interface, Attribute
from zope.component import getUtility

from zope.schema import Datetime, Int, Choice, Text, TextLine, Bool

from canonical.launchpad import _
from canonical.launchpad.fields import (ContentNameField, Summary,
    Title)
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.interfaces.launchpad import IHasOwner
from canonical.launchpad.interfaces.mentoringoffer import ICanBeMentored
from canonical.launchpad.interfaces.validation import valid_webref
from canonical.launchpad.interfaces.project import IProject
from canonical.launchpad.interfaces.sprint import ISprint
from canonical.launchpad.interfaces.specificationtarget import (
    IHasSpecifications)

from canonical.lazr import (
    DBEnumeratedType, DBItem, EnumeratedType, Item)


class SpecificationImplementationStatus(DBEnumeratedType):
    """The Specification Delivery Status

    This tracks the implementation or delivery of the feature being
    specified. The status values indicate the progress that is being made
    in the actual coding or configuration that is needed to realise the
    feature.

    Note that some of the states associated with this schema correlate
    to a "not started" definition. See Specification.started_clause for
    further information, and make sure that it is updated (together with
    the relevant database checks) if additional states are added that
    are also "not started".
    """
    # The `UNKNOWN` state is considered "not started"
    UNKNOWN = DBItem(0, """
        Unknown

        We have no information on the implementation of this feature.
        """)

    # The `NOTSTARTED` state is considered "not started"
    NOTSTARTED = DBItem(5, """
        Not started

        No work has yet been done on the implementation of this feature.
        """)

    # The `DEFERRED` state is considered "not started"
    DEFERRED = DBItem(10, """
        Deferred

        There is no chance that this feature will actually be delivered in
        the targeted release. The specification has effectively been
        deferred to a later date of implementation.
        """)

    NEEDSINFRASTRUCTURE = DBItem(40, """
        Needs Infrastructure

        Work cannot proceed, because the feature depends on
        infrastructure (servers, databases, connectivity, system
        administration work) that has not been supplied.
        """)

    BLOCKED = DBItem(50, """
        Blocked

        Work cannot proceed on this specification because it depends on
        a separate feature that has not yet been implemented.
        (The specification for that feature should be listed as a blocker of
        this one.)
        """)

    STARTED = DBItem(60, """
        Started

        Work has begun, but has not yet been published
        except as informal branches or patches. No indication is given as to
        whether or not this work will be completed for the targeted release.
        """)

    SLOW = DBItem(65, """
        Slow progress

        Work has been slow on this item, and it has a high risk of not being
        delivered on time. Help is wanted with the implementation.
        """)

    GOOD = DBItem(70, """
        Good progress

        The feature is considered on track for delivery in the targeted release.
        """)

    BETA = DBItem(75, """
        Beta Available

        A beta version, implementing substantially all of the feature,
        has been published for widespread testing in personal package
        archives or a personal release. The code is not yet in the
        main archive or mainline branch. Testing and feedback are solicited.
        """)

    NEEDSREVIEW = DBItem(80, """
        Needs Code Review

        The developer is satisfied that the feature has been well
        implemented. It is now ready for review and final sign-off,
        after which it will be marked implemented or deployed.
        """)

    AWAITINGDEPLOYMENT = DBItem(85, """
        Deployment

        The implementation has been done, and can be deployed in the production
        environment, but this has not yet been done by the system
        administrators. (This status is typically used for Web services where
        code is not released but instead is pushed into production.
        """)

    IMPLEMENTED = DBItem(90, """
        Implemented

        This functionality has been delivered for the targeted release, the
        code has been uploaded to the main archives or committed to the
        targeted product series, and no further work is necessary.
        """)

    INFORMATIONAL = DBItem(95, """
        Informational

        This specification is informational, and does not require
        any implementation.
        """)


class SpecificationLifecycleStatus(DBEnumeratedType):
    """The current "lifecycle" status of a specification.

    Specs go from NOTSTARTED, to STARTED, to COMPLETE.
    """

    NOTSTARTED = DBItem(10, """
        Not started

        No work has yet been done on this feature.
        """)

    STARTED = DBItem(20, """
        Started

        This feature is under active development.
        """)

    COMPLETE = DBItem(30, """
        Complete

        This feature has been marked "complete" because no further work is
        expected. Either the feature is done, or it has been abandoned.
        """)


class SpecificationPriority(DBEnumeratedType):
    """The Priority with a Specification must be implemented.

    This enum is used to prioritise work.
    """

    NOTFORUS = DBItem(0, """
        Not

        This feature has been proposed but the project leaders have decided
        that it is not appropriate for inclusion in the mainline codebase.
        See the status whiteboard or the
        specification itself for the rationale for this decision. Of course,
        you are welcome to implement it in any event and publish that work
        for consideration by the community and end users, but it is unlikely
        to be accepted by the mainline developers.
        """)

    UNDEFINED = DBItem(5, """
        Undefined

        This feature has recently been proposed and has not yet been
        evaluated and prioritised by the project leaders.
        """)

    LOW = DBItem(10, """
        Low

        We would like to have it in the
        code, but it's not on any critical path and is likely to get bumped
        in favour of higher-priority work. The idea behind the specification
        is sound and the project leaders would incorporate this
        functionality if the work was done. In general, "low" priority
        specifications will not get core resources assigned to them.
        """)

    MEDIUM = DBItem(50, """
        Medium

        The project developers will definitely get to this feature,
        but perhaps not in the next major release or two.
        """)

    HIGH = DBItem(70, """
        High

        Strongly desired by the project leaders.
        The feature will definitely get review time, and contributions would
        be most effective if directed at a feature with this priority.
        """)

    ESSENTIAL = DBItem(90, """
        Essential

        The specification is essential for the next release, and should be
        the focus of current development. Use this state only for the most
        important of all features.
        """)


class SpecificationFilter(DBEnumeratedType):
    """The kinds of specifications that a listing should include.

    This is used by browser classes that are generating a list of
    specifications for a person, or product, or project, to indicate what
    kinds of specs they want returned. The different filters can be OR'ed so
    that multiple pieces of information can be used for the filter.
    """
    ALL = DBItem(0, """
        All

        This indicates that the list should simply include ALL
        specifications for the underlying object (person, product etc).
        """)

    COMPLETE = DBItem(5, """
        Complete

        This indicates that the list should include only the complete
        specifications for this object.
        """)

    INCOMPLETE = DBItem(10, """
        Incomplete

        This indicates that the list should include the incomplete items
        only. The rules for determining if a specification is incomplete are
        complex, depending on whether or not the spec is informational.
        """)

    INFORMATIONAL = DBItem(20, """
        Informational

        This indicates that the list should include only the informational
        specifications.
        """)

    PROPOSED = DBItem(30, """
        Proposed

        This indicates that the list should include specifications that have
        been proposed as goals for the underlying objects, but not yet
        accepted or declined.
        """)

    DECLINED = DBItem(40, """
        Declined

        This indicates that the list should include specifications that were
        declined as goals for the underlying productseries or distroseries.
        """)

    ACCEPTED = DBItem(50, """
        Accepted

        This indicates that the list should include specifications that were
        accepted as goals for the underlying productseries or distroseries.
        """)

    VALID = DBItem(55, """
        Valid

        This indicates that the list should include specifications that are
        not obsolete or superseded.
        """)

    CREATOR = DBItem(60, """
        Creator

        This indicates that the list should include specifications that the
        person registered in Launchpad.
        """)

    ASSIGNEE = DBItem(70, """
        Assignee

        This indicates that the list should include specifications that the
        person has been assigned to implement.
        """)

    APPROVER = DBItem(80, """
        Approver

        This indicates that the list should include specifications that the
        person is supposed to review and approve.
        """)

    DRAFTER = DBItem(90, """
        Drafter

        This indicates that the list should include specifications that the
        person is supposed to draft. The drafter is usually only needed
        during spec sprints when there's a bottleneck on guys who are
        assignees for many specs.
        """)

    SUBSCRIBER = DBItem(100, """
        Subscriber

        This indicates that the list should include all the specifications
        to which the person has subscribed.
        """)

    FEEDBACK = DBItem(110, """
        Feedback

        This indicates that the list should include all the specifications
        which the person has been asked to provide specific feedback on.
        """)


class SpecificationSort(EnumeratedType):
    """The scheme to sort the results of a specifications query.

    This is usually used in interfaces which ask for a filtered list of
    specifications, so that you can tell which specifications you would
    expect to see first.
    """
    DATE = Item("""
        Date

        This indicates a preferred sort order of date of creation, newest
        first.
        """)

    PRIORITY = Item("""
        Priority

        This indicates a preferred sort order of priority (highest first)
        followed by status. This is the default sort order when retrieving
        specifications from the system.
        """)


class SpecificationDefinitionStatus(DBEnumeratedType):
    """The current status of a Specification.

    This enum tells us whether or not a specification is approved, or still
    being drafted, or implemented, or obsolete in some way. The ordinality
    of the values is important, it's the order (lowest to highest) in which
    we probably want them displayed by default.
    """

    APPROVED = DBItem(10, """
        Approved

        The project team believe that the specification is ready to be
        implemented, without substantial issues being encountered.
        """)

    PENDINGAPPROVAL = DBItem(15, """
        Pending Approval

        Reviewed and considered ready for final approval.
        The reviewer believes the specification is clearly written,
        and adequately addresses all important issues that will
        be raised during implementation.
        """)

    PENDINGREVIEW = DBItem(20, """
        Review

        Has been put in a reviewer's queue. The reviewer will
        assess it for clarity and comprehensiveness, and decide
        whether further work is needed before the spec can be considered for
        actual approval.
        """)

    DRAFT = DBItem(30, """
        Drafting

        The specification is actively being drafted, with a drafter in place
        and frequent revision occurring.
        Do not park specs in the "drafting" state indefinitely.
        """)

    DISCUSSION = DBItem(35, """
        Discussion

        Still needs active discussion, at a sprint for example.
        """)

    NEW = DBItem(40, """
        New

        No thought has yet been given to implementation strategy, dependencies,
        or presentation/UI issues.
        """)

    SUPERSEDED = DBItem(60, """
        Superseded

        Still interesting, but superseded by a newer spec or set of specs that
        clarify or describe a newer way to implement the desired feature.
        Please use the newer specs and not this one.
        """)

    OBSOLETE = DBItem(70, """
        Obsolete

        The specification has been obsoleted, probably because it was decided
        against. People should not put any effort into implementing it.
        """)


class SpecificationGoalStatus(DBEnumeratedType):
    """The target status for this specification.

    This enum allows us to show whether or not the specification has been
    approved or declined as a target for the given productseries or
    distroseries.
    """

    ACCEPTED = DBItem(10, """
        Accepted

        The drivers have confirmed that this specification is targeted to
        the stated distribution release or product series.
        """)

    DECLINED = DBItem(20, """
        Declined

        The drivers have decided not to accept this specification as a goal
        for the stated distribution release or product series.
        """)

    PROPOSED = DBItem(30, """
        Proposed

        This spec has been submitted as a potential goal for the stated
        product series or distribution release, but the drivers have not yet
        accepted or declined that goal.
        """)


class SpecNameField(ContentNameField):

    errormessage = _("%s is already in use by another blueprint.")

    @property
    def _content_iface(self):
        return ISpecification

    def _getByName(self, name):
        """Finds a specification by name from the current context.

        Returns a specification if (and only if) the current context
        defines a unique specification namespace and then if a matching
        specification can be found within that namespace. Returns None
        otherwise.
        """
        if ISpecificationSet.providedBy(self.context):
            # The context is the set of all specifications. Since this
            # set corresponds to multiple specification namespaces, we
            # return None.
            return None
        elif IProject.providedBy(self.context):
            # The context is a project group. Since a project group
            # corresponds to multiple specification namespaces, we
            # return None.
            return None
        elif ISpecification.providedBy(self.context):
            # The context is a specification. Since a specification's
            # target defines a single specification namespace, we ask
            # the target to perform the lookup.
            return self.context.target.getSpecification(name)
        elif ISprint.providedBy(self.context):
            # The context is a sprint. Since a sprint corresponds
            # to multiple specification namespaces, we return None.
            return None
        else:
            # The context is a entity such as a product or distribution.
            # Since this type of context is associated with exactly one
            # specification namespace, we ask the context to perform the
            # lookup.
            return self.context.getSpecification(name)


class SpecURLField(TextLine):

    errormessage = _("%s is already registered by another blueprint.")

    def _validate(self, specurl):
        TextLine._validate(self, specurl)
        if (ISpecification.providedBy(self.context) and
            specurl == getattr(self.context, 'specurl')):
            # The specurl wasn't changed
            return

        specification = getUtility(ISpecificationSet).getByURL(specurl)
        if specification is not None:
            raise LaunchpadValidationError(self.errormessage % specurl)


class INewSpecification(Interface):
    """A schema for a new specification."""

    name = SpecNameField(
        title=_('Name'), required=True, readonly=False,
        description=_(
            "May contain lower-case letters, numbers, and dashes. "
            "It will be used in the specification url. "
            "Examples: mozilla-type-ahead-find, postgres-smart-serial.")
        )
    title = Title(
        title=_('Title'), required=True, description=_(
            "Describe the feature as clearly as possible in up to 70 characters. "
            "This title is displayed in every feature list or report."))
    specurl = SpecURLField(
        title=_('Specification URL'), required=False,
        description=_(
            "The URL of the specification. This is usually a wiki page."),
        constraint=valid_webref)
    summary = Summary(
        title=_('Summary'), required=True, description=_(
            "A single-paragraph description of the feature. "
            "This will also be displayed in most feature listings."))
    definition_status = Choice(
        title=_('Definition Status'),
        vocabulary=SpecificationDefinitionStatus,
        default=SpecificationDefinitionStatus.NEW,
        description=_(
            "The current status of the process to define the "
            "feature and get approval for the implementation plan."))
    assignee = Choice(title=_('Assignee'), required=False,
        description=_("The person responsible for implementing the feature."),
        vocabulary='ValidPersonOrTeam')
    drafter = Choice(title=_('Drafter'), required=False,
        description=_("The person responsible for drafting the specification."),
        vocabulary='ValidPersonOrTeam')
    approver = Choice(title=_('Approver'), required=False,
        description=_(
            "The person responsible for approving the specification, "
            "and for reviewing the code when it's ready to be landed."),
        vocabulary='ValidPersonOrTeam')


class INewSpecificationProjectTarget(Interface):
    """A mixin schema for a new specification.

    Requires the user to specify a product from a given project.
    """
    target = Choice(title=_("For"),
                    description=_("The project for which this "
                                  "proposal is being made."),
                    required=True, vocabulary='ProjectProducts')


class INewSpecificationSeriesGoal(Interface):
    """A mixin schema for a new specification.

    Allows the user to propose the specification as a series goal.
    """
    goal = Bool(title=_('Propose for series goal'),
                description=_("Check this to indicate that you wish to "
                              "propose this blueprint as a series goal."),
                required=True, default=False)


class INewSpecificationSprint(Interface):
    """A mixin schema for a new specification.

    Allows the user to propose the specification for discussion at a sprint.
    """
    sprint = Choice(title=_("Propose for sprint"),
                    description=_("The sprint to which agenda this "
                                  "blueprint is being suggested."),
                    required=False, vocabulary='FutureSprint')


class INewSpecificationTarget(Interface):
    """A mixin schema for a new specification.

    Requires the user to specify a distribution or a product as a target.
    """
    target = Choice(title=_("For"),
                    description=_("The project for which this proposal is "
                                  "being made."),
                    required=True, vocabulary='DistributionOrProduct')


class ISpecification(INewSpecification, INewSpecificationTarget, IHasOwner,
    ICanBeMentored):
    """A Specification."""

    # TomBerger 2007-06-20: 'id' is required for
    #      SQLObject to be able to assign a security-proxied
    #      specification to an attribute of another SQL object
    #      referencing it.
    id = Int(title=_("Database ID"), required=True, readonly=True)

    priority = Choice(
        title=_('Priority'), vocabulary=SpecificationPriority,
        default=SpecificationPriority.UNDEFINED, required=True)
    datecreated = Datetime(
        title=_('Date Created'), required=True, readonly=True)
    owner = Choice(title=_('Owner'), required=True, readonly=True,
        vocabulary='ValidPersonOrTeam')
    # target
    product = Choice(title=_('Project'), required=False,
        vocabulary='Product')
    distribution = Choice(title=_('Distribution'), required=False,
        vocabulary='Distribution')

    # series
    productseries = Choice(title=_('Series Goal'), required=False,
        vocabulary='FilteredProductSeries',
        description=_(
            "Choose a series in which you would like to deliver "
            "this feature. Selecting '(no value)' will clear the goal."))
    distroseries = Choice(title=_('Series Goal'), required=False,
        vocabulary='FilteredDistroSeries',
        description=_(
            "Choose a series in which you would like to deliver "
            "this feature. Selecting '(no value)' will clear the goal."))

    # milestone
    milestone = Choice(
        title=_('Milestone'), required=False, vocabulary='Milestone',
        description=_(
            "The milestone in which we would like this feature to be "
            "delivered."))

    # nomination to a series for release management
    goal = Attribute("The series for which this feature is a goal.")
    goalstatus = Choice(
        title=_('Goal Acceptance'), vocabulary=SpecificationGoalStatus,
        default=SpecificationGoalStatus.PROPOSED, description=_(
            "Whether or not the drivers have accepted this feature as "
            "a goal for the targeted series."))
    goal_proposer = Attribute("The person who nominated the spec for "
        "this series.")
    date_goal_proposed = Attribute("The date of the nomination.")
    goal_decider = Attribute("The person who approved or declined "
        "the spec a a goal.")
    date_goal_decided = Attribute("The date the spec was approved "
        "or declined as a goal.")

    whiteboard = Text(title=_('Status Whiteboard'), required=False,
        description=_(
            "Any notes on the status of this spec you would like to make. "
            "Your changes will override the current text."))
    direction_approved = Bool(title=_('Basic direction approved?'),
        required=False, default=False, description=_("Check this to "
        "indicate that the drafter and assignee have satisfied the "
        "approver that they are headed in the right basic direction "
        "with this specification."))
    man_days = Int(title=_("Estimated Developer Days"),
        required=False, default=None, description=_("An estimate of the "
        "number of developer days it will take to implement this feature. "
        "Please only provide an estimate if you are relatively confident "
        "in the number."))
    implementation_status = Choice(title=_("Implementation Status"),
        required=True, default=SpecificationImplementationStatus.UNKNOWN,
        vocabulary=SpecificationImplementationStatus, description=_(
        "The state of progress being made on the actual implementation or "
        "delivery of this feature."))
    superseded_by = Choice(title=_("Superseded by"),
        required=False, default=None,
        vocabulary='Specification', description=_("The specification "
        "which supersedes this one. Note that selecting a specification "
        "here and pressing Continue will change the specification "
        "status to Superseded."))

    # lifecycle
    starter = Attribute('The person who first set the state of the '
        'spec to the values that we consider mark it as started.')
    date_started = Attribute('The date when this spec was marked '
        'started.')
    completer = Attribute('The person who finally set the state of the '
        'spec to the values that we consider mark it as complete.')
    date_completed = Attribute('The date when this spec was marked '
        'complete. Note that complete also includes "obsolete" and '
        'superseded. Essentially, it is the state where no more work '
        'will be done on the feature.')

    # joins
    subscriptions = Attribute('The set of subscriptions to this spec.')
    subscribers = Attribute('The set of subscribers to this spec.')
    sprints = Attribute('The sprints at which this spec is discussed.')
    sprint_links = Attribute('The entries that link this spec to sprints.')
    feedbackrequests = Attribute('The set of feedback requests queued.')
    dependencies = Attribute('Specs on which this spec depends.')
    blocked_specs = Attribute('Specs for which this spec is a dependency.')
    all_deps = Attribute(
        "All the dependencies, including dependencies of dependencies.")
    all_blocked = Attribute(
        "All specs blocked on this, and those blocked on the blocked ones.")
    branch_links = Attribute('The entries that link the branches to the spec')

    # emergent properties
    informational = Attribute('Is True if this spec is purely informational '
        'and requires no implementation.')
    is_complete = Attribute('Is True if this spec is already completely '
        'implemented. Note that it is True for informational specs, since '
        'they describe general functionality rather than specific '
        'code to be written. It is also true of obsolete and superseded '
        'specs, since there is no longer any need to schedule work for '
        'them.')
    is_incomplete = Attribute('Is True if this work still needs to '
        'be done. Is in fact always the opposite of is_complete.')
    is_blocked = Attribute('Is True if this spec depends on another spec '
        'which is still incomplete.')
    is_started = Attribute('Is True if the spec is in a state which '
        'we consider to be "started". This looks at the delivery '
        'attribute, and also considers informational specs to be '
        'started when they are approved.')

    def retarget(product=None, distribution=None):
        """Retarget the spec to a new product or distribution. One of
        product or distribution must be None (but not both).
        """

    def getSprintSpecification(sprintname):
        """Get the record that links this spec to the named sprint."""

    def getFeedbackRequests(person):
        """Return the requests for feedback for a given person on this
        specification.
        """

    def notificationRecipientAddresses():
        """Return the list of email addresses that receive notifications."""

    # goal management
    def proposeGoal(goal, proposer):
        """Propose this spec for a series or distroseries."""

    def acceptBy(decider):
        """Mark the spec as being accepted for its current series goal."""

    def declineBy(decider):
        """Mark the spec as being declined as a goal for the proposed series."""

    has_accepted_goal = Attribute('Is true if this specification has been '
        'proposed as a goal for a specific series, '
        'and the drivers of that series have accepted the goal.')

    # lifecycle management
    def updateLifecycleStatus(user):
        """Mark the specification as started, and/or complete, if appropriate.

        This will verify that the state of the specification is in fact
        "complete" (there is a completeness test in
        Specification.is_complete) and then record the completer and the
        date_completed. If the spec is not completed, then it ensures that
        nothing is recorded about its completion.

        It returns a SpecificationLifecycleStatus dbschema showing the
        overall state of the specification IF the state has changed.

        """

    # event-related methods
    def getDelta(old_spec, user):
        """Return a dictionary of things that changed between this spec and
        the old_spec.

        This method is primarily used by event subscription code, to
        determine what has changed during an SQLObjectModifiedEvent.
        """

    # subscription-related methods
    def subscription(person):
        """Return the subscription for this person to this spec, or None."""

    def subscribe(person, essential=False):
        """Subscribe this person to the feature specification."""

    def unsubscribe(person):
        """Remove the person's subscription to this spec."""

    def getSubscriptionByName(name):
        """Return a subscription based on the person's name, or None."""

    def isSubscribed(person):
        """Is person subscribed to this spec?

        Returns True if the user is explicitly subscribed to this spec
        (no matter what the type of subscription), otherwise False.

        If person is None, the return value is always False.
        """

    # queue-related methods
    def queue(provider, requester, queuemsg=None):
        """Put this specification into the feedback queue of the given person,
        with an optional message."""

    def unqueue(provider, requester):
        """Remove the feedback request by the requester for this spec, from
        the provider's feedback queue.
        """

    # sprints
    def linkSprint(sprint, user):
        """Put this spec on the agenda of the sprint."""

    def unlinkSprint(sprint):
        """Remove this spec from the agenda of the sprint."""

    # dependencies
    def createDependency(specification):
        """Create a dependency for this spec on the spec provided."""

    def removeDependency(specification):
        """Remove any dependency of this spec on the spec provided."""

    # branches
    def getBranchLink(branch):
        """Return the SpecificationBranch link for the branch, or None."""

    def linkBranch(branch, summary=None):
        """Link the given branch to this specification."""


# Interfaces for containers
class ISpecificationSet(IHasSpecifications):
    """A container for specifications."""

    displayname = Attribute('Displayname')

    title = Attribute('Title')

    coming_sprints = Attribute("The next 5 sprints in the system.")

    specification_count = Attribute(
        "The total number of blueprints in Launchpad")

    def __iter__():
        """Iterate over all specifications."""

    def getByURL(url):
        """Return the specification with the given url."""

    def new(name, title, specurl, summary, priority, status, owner,
        assignee=None, drafter=None, approver=None, product=None,
        distribution=None):
        """Create a new specification."""


class ISpecificationDelta(Interface):
    """The quantitative changes made to a spec that was edited."""

    specification = Attribute("The ISpec, after it's been edited.")
    user = Attribute("The IPerson that did the editing.")

    # fields on the spec itself, we provide just the new changed value
    title = Attribute("The spec title or None.")
    summary = Attribute("The spec summary or None.")
    whiteboard = Attribute("The spec whiteboard or None.")
    specurl = Attribute("The URL to the spec home page (not in Launchpad).")
    productseries = Attribute("The product series.")
    distroseries = Attribute("The series to which this is targeted.")
    milestone = Attribute("The milestone to which the spec is targeted.")
    bugs_linked = Attribute("A list of new bugs linked to this spec.")
    bugs_unlinked = Attribute("A list of bugs unlinked from this spec.")

    # items where we provide 'old' and 'new' values if they changed
    name = Attribute("Old and new names, or None.")
    priority = Attribute("Old and new priorities, or None")
    definition_status = Attribute("Old and new statuses, or None")
    target = Attribute("Old and new target, or None")
    approver = Attribute("Old and new approver, or None")
    assignee = Attribute("Old and new assignee, or None")
    drafter = Attribute("Old and new drafter, or None")
