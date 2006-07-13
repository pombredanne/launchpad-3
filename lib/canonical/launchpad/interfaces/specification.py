# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Specification interfaces."""

__metaclass__ = type

__all__ = [
    'ISpecification',
    'ISpecificationSet',
    'ISpecificationDelta',
    ]


from zope.interface import Interface, Attribute
from zope.component import getUtility

from zope.schema import Datetime, Int, Choice, Text, TextLine, Bool, Field

from canonical.launchpad import _
from canonical.launchpad.fields import (ContentNameField, Summary,
    Title)
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.interfaces import IHasOwner
from canonical.launchpad.interfaces.validation import valid_webref
from canonical.launchpad.interfaces.specificationtarget import (
    IHasSpecifications)

from canonical.lp.dbschema import (
    SpecificationStatus, SpecificationPriority, SpecificationDelivery,
    SpecificationGoalStatus)


class SpecNameField(ContentNameField):

    errormessage = _("%s is already in use by another specification.")

    @property
    def _content_iface(self):
        return ISpecification

    def _getByName(self, name):
        if ISpecification.providedBy(self.context):
            return self.context.target.getSpecification(name)
        else:
            return self.context.getSpecification(name)


class SpecURLField(TextLine):

    errormessage = _("%s is already registered by another specification.")

    def _validate(self, specurl):
        TextLine._validate(self, specurl)
        if (ISpecification.providedBy(self.context) and
            specurl == getattr(self.context, 'specurl')):
            # The specurl wasn't changed
            return

        specification = getUtility(ISpecificationSet).getByURL(specurl)
        if specification is not None:
            raise LaunchpadValidationError(self.errormessage % specurl)


class ISpecification(IHasOwner):
    """A Specification."""

    name = SpecNameField(
        title=_('Name'), required=True, description=_(
            "May contain letters, numbers, and dashes only, because it is "
            "used in the specification url. "
            "Examples: mozilla-type-ahead-find, postgres-smart-serial."),
        constraint=name_validator)
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
    status = Choice(
        title=_('Definition Status'), vocabulary='SpecificationStatus',
        default=SpecificationStatus.BRAINDUMP, description=_(
            "The current status of the process to define the "
            "feature and get approval for the implementation plan."))
    priority = Choice(
        title=_('Priority'), vocabulary='SpecificationPriority',
        default=SpecificationPriority.UNDEFINED, required=True)
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
    datecreated = Datetime(
        title=_('Date Created'), required=True, readonly=True)
    owner = Choice(title=_('Owner'), required=True, readonly=True,
        vocabulary='ValidPersonOrTeam')
    milestone = Choice(
        title=_('Milestone'), required=False, vocabulary='Milestone',
        description=_(
            "The milestone in which we would like this feature to be "
            "delivered."))
    productseries = Choice(title=_('Series Goal'), required=False,
        vocabulary='FilteredProductSeries',
        description=_(
            "Choose a release series in which you would like to deliver "
            "this feature. Selecting '(no value)' will clear the goal."))
    distrorelease = Choice(title=_('Release Goal'), required=False,
        vocabulary='FilteredDistroRelease',
        description=_(
            "Choose a release in which you would like to deliver "
            "this feature. Selecting '(no value)' will clear the goal."))
    goal = Attribute(
        "The product series or distro release for which this feature "
        "is a goal.")
    goalstatus = Choice(
        title=_('Goal Acceptance'), vocabulary='SpecificationGoalStatus',
        default=SpecificationGoalStatus.PROPOSED, description=_(
            "Whether or not the drivers have accepted this feature as "
            "a goal for the targeted release or series."))

    whiteboard = Text(title=_('Status Whiteboard'), required=False,
        description=_(
            "Any notes on the status of this spec you would like to make. "
            "Your changes will override the current text."))
    needs_discussion = Bool(title=_('Needs further discussion?'),
        required=False, description=_("Check this to indicate that the "
        "specification needs further group discussion as well as drafting"
        "."), default=True)
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
    delivery = Choice(title=_("Implementation Status"),
        required=True, default=SpecificationDelivery.UNKNOWN,
        vocabulary='SpecificationDelivery', description=_("The state of "
        "progress being made on the actual implementation or delivery "
        "of this feature."))
    superseded_by = Choice(title=_("Superseded by"),
        required=False, default=None,
        vocabulary='Specification', description=_("The specification "
        "which supersedes this one. Note that selecting a specification "
        "here and pressing Continue will change the specification "
        "status to Superseded."))
    informational = Bool(title=_('Is Informational'),
        required=False, default=False, description=_('Check this box if '
        'this specification is purely documentation or overview and does '
        'not actually involve any implementation.'))
    
    # other attributes
    product = Choice(title=_('Product'), required=False,
        vocabulary='Product')
    distribution = Choice(title=_('Distribution'), required=False,
        vocabulary='Distribution')

    target = Field(
        title=_("The product or distribution to which this spec belongs."),
        readonly=True)

    # joins
    subscriptions = Attribute('The set of subscriptions to this spec.')
    subscribers = Attribute('The set of subscribers to this spec.')
    sprints = Attribute('The sprints at which this spec is discussed.')
    sprint_links = Attribute('The entries that link this spec to sprints.')
    feedbackrequests = Attribute('The set of feedback requests queued.')
    bugs = Field(title=_('Bugs related to this spec'), readonly=True)
    dependencies = Attribute('Specs on which this spec depends.')
    blocked_specs = Attribute('Specs for which this spec is a dependency.')
    all_deps = Attribute(
        "All the dependencies, including dependencies of dependencies.")
    all_blocked = Attribute(
        "All specs blocked on this, and those blocked on the blocked ones.")


    # emergent properties
    is_complete = Attribute('Is True if this spec is already completely '
        'implemented. Note that it is True for informational specs, since '
        'they describe general funcitonality rather than specific '
        'code to be written. It is also true of obsolete and superseded '
        'specs, since there is no longer any need to schedule work for '
        'them.')
    is_incomplete = Attribute('Is True if this work still needs to '
        'be done. Is in fact always the opposite of is_complete.')
    is_blocked = Attribute('Is True if this spec depends on another spec '
        'which is still incomplete.')

    has_release_goal = Attribute('Is true if this specification has been '
        'proposed as a goal for a specific distro release or product '
        'series and the drivers of that release/series have accepted '
        'the goal.')

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

    # event-related methods
    def getDelta(old_spec, user):
        """Return a dictionary of things that changed between this spec and
        the old_spec.

        This method is primarily used by event subscription code, to
        determine what has changed during an SQLObjectModifiedEvent.
        """

    # subscription-related methods
    def subscribe(person):
        """Subscribe this person to the feature specification."""
        
    def unsubscribe(person):
        """Remove the person's subscription to this spec."""

    # queue-related methods
    def queue(provider, requester, queuemsg=None):
        """Put this specification into the feedback queue of the given person,
        with an optional message."""
        
    def unqueue(provider, requester):
        """Remove the feedback request by the requester for this spec, from
        the provider's feedback queue.
        """

    # bug linking
    def linkBug(bug_number):
        """Link this spec to the given bug number, returning the
        SpecificationBug linker.
        """

    def unLinkBug(bug_number):
        """Remove any link to this bug number, and return None."""

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


# Interfaces for containers
class ISpecificationSet(IHasSpecifications):
    """A container for specifications."""

    displayname = Attribute('Displayname')

    title = Attribute('Title')

    latest_specs = Attribute(
        "The latest 10 specifications registered in Launchpad.")

    upcoming_sprints = Attribute("The next 5 sprints in the system.")

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
    distrorelease = Attribute("The release to which this is targeted.")
    milestone = Attribute("The milestone to which the spec is targeted.")
    bugs_linked = Attribute("A list of new bugs linked to this spec.")
    bugs_unlinked = Attribute("A list of bugs unlinked from this spec.")

    # items where we provide 'old' and 'new' values if they changed
    name = Attribute("Old and new names, or None.")
    priority = Attribute("Old and new priorities, or None")
    status = Attribute("Old and new statuses, or None")
    target = Attribute("Old and new target, or None")
    approver = Attribute("Old and new approver, or None")
    assignee = Attribute("Old and new assignee, or None")
    drafter = Attribute("Old and new drafter, or None")
