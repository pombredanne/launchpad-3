# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Bounty interfaces."""

__metaclass__ = type

__all__ = [
    'IBounty',
    'IBountySet',
    ]

from zope.i18nmessageid import MessageIDFactory

from zope.interface import Attribute

from zope.schema import Datetime, Int, Choice, Text, TextLine, Float
from zope.app.form.browser.interfaces import IAddFormCustomization

from canonical.launchpad.fields import Summary, Title, TimeInterval
from canonical.launchpad.validators.name import valid_name
from canonical.launchpad.interfaces import IHasOwner, IMessageTarget
from canonical.lp.dbschema import BountyDifficulty, BountyStatus

_ = MessageIDFactory('launchpad')

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
            constraint=valid_name,
            )
    title = Title(
            title=_('Title'), required=True,
            description=_("""Describe the task as clearly as
            possible in up to 70 characters. This title is
            displayed in every bounty list or report."""),
            )
    summary = Summary(
            title=_('Summary'), required=True,
            description=_("""A single-paragraph description of the
            bounty. This will also be displayed in most
            bounty listings."""),
            )
    description = Text(
            title=_('Description'), required=True,
            description=_("""A detailed description. Include exact
            results that will be acceptable to the bounty owner and
            reviewer.""")
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
        default=BountyStatus.OPEN, description=_("The current "
        "status of this bounty."))
    difficulty = Choice(
        title=_('Difficulty'), vocabulary='BountyDifficulty',
        default=BountyDifficulty.NORMAL, description=_("The difficulty "
        "of this bounty. Try to find the option that best matches the "
        "work to be done."))
    reviewer = Choice(title=_('The bounty reviewer.'), required=False,
        description=_("The person who is responsible for deciding whether "
        "the bounty is awarded, and to whom if there are multiple "
        "claimants."), vocabulary='ValidPersonOrTeamVocabulary')
    datecreated = Datetime(
            title=_('Date Created'), required=True, readonly=True,
            )
    ownerID = Int(
            title=_('Owner'), required=True, readonly=True
            )
    owner = Attribute("The owner's IPerson")

    # joins
    subscriptions = Attribute('The set of subscriptions to this bounty.')
    projects = Attribute('The projects which this bounty is related to.')
    products = Attribute('The products to which this bounty is related.')
    distributions = Attribute('The distributions to which this bounty is related.')

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

