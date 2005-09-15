# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Specification interfaces."""

__metaclass__ = type

__all__ = [
    'ISpecification',
    'ISpecificationSet',
    ]

from zope.i18nmessageid import MessageIDFactory

from zope.interface import Interface, Attribute

from zope.schema import Datetime, Int, Choice, Text, TextLine, Float

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
        title=_('Specification URL'), required=True,
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
        default=SpecificationPriority.MEDIUM)
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
        vocabulary='FilteredProductSeries', description=_(
            "The release series to which this feature is targeted."))
    distrorelease = Choice(title=_('Targeted Release'), required=False,
        vocabulary='FilteredDistroRelease', description=_('Select '
        'the distribution release to which this feature is targeted.'))
    whiteboard = Text(title=_('Status Whiteboard'), required=False,
        description=_(
            "Any notes on the status of this spec you would like to make. "
            "Your changes will override the current text."))
    # other attributes
    product = Attribute('The product to which this feature belongs.')
    distribution = Attribute('The distribution to which this spec belongs.')
    target = Attribute(
        "The product or distribution to which this spec belongs.")
    # joins
    subscriptions = Attribute('The set of subscriptions to this spec.')
    sprints = Attribute('The sprints at which this spec is discussed.')
    reviews = Attribute('The set of reviews queued.')
    bugs = Attribute('Bugs related to this spec')
    dependencies = Attribute('Specs on which this spec depends.')
    blocked_specs = Attribute('Specs for which this spec is a dependency.')

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

