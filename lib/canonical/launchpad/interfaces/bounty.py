# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Bounty interfaces."""

__metaclass__ = type

__all__ = [
    'IBounty',
    'IBountySet',
    ]


from zope.interface import Attribute

from zope.schema import Datetime, Int, Choice, Text, TextLine, Float
from zope.app.form.browser.interfaces import IAddFormCustomization

from canonical.launchpad import _
from canonical.launchpad.fields import Summary, Title
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.interfaces import IHasOwner, IMessageTarget
from canonical.lp.dbschema import BountyDifficulty, BountyStatus


class IBounty(IHasOwner, IMessageTarget):
    """The core bounty description."""

    id = Int(
            title=_('Bounty ID'), required=True, readonly=True,
            )
    name = TextLine(
            title=_('Name'), required=True,
            description=_("""Keep this name very short, unique, and
            descriptive, because it will be used in URLs. Examples:
            mozilla-type-ahead-find, postgres-smart-serial."""),
            constraint=name_validator,
            )
    title = Title(
            title=_('Title'), required=True
            )
    summary = Summary(
            title=_('Summary'), required=True
            )
    description = Text(
            title=_('Description'), required=True,
            description=_("""Include exact results that will be acceptable to
            the bounty owner and reviewer, and contact details for the person
            coordinating the bounty.""")
            )
    usdvalue = Float(
            title=_('Estimated value (US dollars)'),
            required=True, description=_("""In some cases the
            bounty may have been offered in a variety of
            currencies, so this USD value is an estimate based
            on recent currency rates.""")
            )
    bountystatus = Choice(
        title=_('Status'), vocabulary='BountyStatus',
        default=BountyStatus.OPEN)
    difficulty = Choice(
        title=_('Difficulty'), vocabulary='BountyDifficulty',
        default=BountyDifficulty.NORMAL)
    reviewer = Choice(title=_('The bounty reviewer.'), required=False,
        description=_("The person who is responsible for deciding whether "
        "the bounty is awarded, and to whom if there are multiple "
        "claimants."), vocabulary='ValidPersonOrTeam')
    datecreated = Datetime(
            title=_('Date Created'), required=True, readonly=True,
            )
    owner = Choice(
        title=_('Owner'),
        required=True,
        vocabulary='ValidOwner',
        description=_("""Owner (registrant) of Bounty."""))
    # XXX kiko 2005-01-14:
    # is this really necessary? IDs shouldn't be exposed in interfaces.
    ownerID = Int(
            title=_('Owner'), required=True, readonly=True
            )

    # joins
    subscriptions = Attribute('The set of subscriptions to this bounty.')
    projects = Attribute('The project groups which this bounty is related to.')
    products = Attribute('The projects to which this bounty is related.')
    distributions = Attribute(
        'The distributions to which this bounty is related.')

    # subscription-related methods
    def subscribe(person):
        """Subscribe this person to the bounty."""

    def unsubscribe(person):
        """Remove this person's subscription to this bounty."""


# Interfaces for containers
class IBountySet(IAddFormCustomization):
    """A container for bounties."""

    title = Attribute('Title')

    top_bounties = Attribute('The top 5 bounties in the system')

    def __getitem__(key):
        """Get a bounty."""

    def __iter__():
        """Iterate through the bounties in this set."""

    def new(name, title, summary, description, usdvalue, owner, reviewer):
        """Create a new bounty."""

