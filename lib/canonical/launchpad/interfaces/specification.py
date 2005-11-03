# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Specification interfaces."""

__metaclass__ = type

__all__ = [
    'ISpecification',
    'ISpecificationSet',
    'ISpecificationDelta',
    ]

from zope.i18nmessageid import MessageIDFactory

from zope.interface import Interface, Attribute

from zope.schema import Datetime, Int, Choice, Text, TextLine, Float, Bool

from canonical.launchpad.fields import Summary, Title, TimeInterval
from canonical.launchpad.validators.name import valid_name
from canonical.launchpad.interfaces import IHasOwner
from canonical.launchpad.interfaces.validation import valid_webref
from canonical.lp.dbschema import SpecificationStatus, SpecificationPriority


_ = MessageIDFactory('launchpad')


class ISpecification(IHasOwner):
    """The core bounty description."""

    # id = Int(title=_('Specification ID'), required=True, readonly=True)
    name = TextLine(
        title=_('Name'), required=True, description=_(
            "May contain letters, numbers, and dashes only. "
            "Examples: mozilla-type-ahead-find, postgres-smart-serial."),
        constraint=valid_name)
    title = Title(
        title=_('Title'), required=True, description=_(
            "Describe the feature as clearly as possible in up to 70 characters. "
            "This title is displayed in every feature list or report."))
    specurl = TextLine(
        title=_('Specification URL'), required=False,
        description=_(
            "The URL of the specification. This is usually a wiki page."),
        constraint=valid_webref)
    summary = Summary(
        title=_('Summary'), required=True, description=_(
            "A single-paragraph description of the feature. "
            "This will also be displayed in most feature listings."))
    status = Choice(
        title=_('Status'), vocabulary='SpecificationStatus',
        default=SpecificationStatus.BRAINDUMP)
    priority = Choice(
        title=_('Priority'), vocabulary='SpecificationPriority',
        default=SpecificationPriority.PROPOSED, required=True)
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
            "The milestone in which we would like this feature to be delivered."))
    productseries = Choice(title=_('Targeted Product Series'), required=False,
        vocabulary='FilteredProductSeries',
        description=_(
            "The release series to which this feature is targeted."))
    distrorelease = Choice(title=_('Targeted Release'), required=False,
        vocabulary='FilteredDistroRelease',
        description=_(
            "The distribution release to which this feature is targeted."))
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
    # other attributes
    product = Choice(title=_('Product'), required=False,
        vocabulary='Product')
    distribution = Choice(title=_('Distribution'), required=False,
        vocabulary='Distribution')
    target = Attribute(
        "The product or distribution to which this spec belongs.")
    # joins
    subscriptions = Attribute('The set of subscriptions to this spec.')
    sprints = Attribute('The sprints at which this spec is discussed.')
    sprint_links = Attribute('The entries that link this spec to sprints.')
    reviews = Attribute('The set of reviews queued.')
    bugs = Attribute('Bugs related to this spec')
    dependencies = Attribute('Specs on which this spec depends.')
    blocked_specs = Attribute('Specs for which this spec is a dependency.')

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

    def retarget(product=None, distribution=None):
        """Retarget the spec to a new product or distribution. One of
        product or distribution must be None (but not both).
        """

    def getSprintSpecification(sprintname):
        """Get the record that links this spec to the named sprint."""

    # event-related methods
    def getDelta(new_spec, user):
        """Return a dictionary of things that changed between this spec and
        the new_spec.

        This method is primarily used by event subscription code, to
        determine what has changed during an SQLObjectModifiedEvent.
        """

    # subscription-related methods
    def subscribe(person):
        """Subscribe this person to the feature specification."""
        
    def unsubscribe(person):
        """Remove the person's subscription to this spec."""

    # queue-related methods
    def queue(person, queuemsg=None):
        """Put this specification into the review queue of the given person,
        with an optional message."""
        
    def unqueue(person):
        """Remove the spec from this person's review queue."""

    # bug linking
    def linkBug(bug_number):
        """Link this spec to the given bug number, returning the
        SpecificationBug linker.
        """

    def unLinkBug(bug_number):
        """Remove any link to this bug number, and return None."""

    # sprints
    def linkSprint(sprint):
        """Put this spec on the agenda of the sprint."""

    def unlinkSprint(sprint):
        """Remove this spec from the agenda of the sprint."""

    # dependencies
    def createDependency(specification):
        """Create a dependency for this spec on the spec provided."""

    def removeDependency(specification):
        """Remove any dependency of this spec on the spec provided."""

    def all_deps(self, higher=[]):
        """All the dependencies, including dependencies of dependencies."""

    def all_blocked(self, higher=[]):
        """All the specs blocked on this, and those blocked on the blocked
        ones.
        """


# Interfaces for containers
class ISpecificationSet(Interface):
    """A container for specifications."""

    title = Attribute('Title')

    latest_specs = Attribute(
        "The latest 10 specifications registered in Launchpad.")

    upcoming_sprints = Attribute("The next 5 sprints in the system.")

    def __iter__():
        """Iterate over all specifications."""

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
