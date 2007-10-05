# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Bounty interfaces."""

__metaclass__ = type

__all__ = [
    'BountyDifficulty',
    'BountyStatus',
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

from canonical.lazr.enum import DBEnumeratedType, DBItem


class BountyDifficulty(DBEnumeratedType):
    """Bounty Difficulty

    An indicator of the difficulty of a particular bounty.
    """

    TRIVIAL = DBItem(10, """
        Trivial

        This bounty requires only very basic skills to complete the task. No
        real domain knowledge is required, only simple system
        administration, writing or configuration skills, and the ability to
        publish the work.""")

    BASIC = DBItem(20, """
        Basic

        This bounty requires some basic programming skills, in a high level
        language like Python or C# or... BASIC. However, the project is
        being done "standalone" and so no knowledge of existing code is
        required.""")

    STRAIGHTFORWARD = DBItem(30, """
        Straightforward

        This bounty is easy to implement but does require some broader
        understanding of the framework or application within which the work
        must be done.""")

    NORMAL = DBItem(50, """
        Normal

        This bounty requires a moderate amount of programming skill, in a
        high level language like HTML, CSS, JavaScript, Python or C#. It is
        an extension to an existing application or package so the work will
        need to follow established project coding standards.""")

    CHALLENGING = DBItem(60, """
        Challenging

        This bounty requires knowledge of a low-level programming language
        such as C or C++.""")

    DIFFICULT = DBItem(70, """
        Difficult

        This project requires knowledge of a low-level programming language
        such as C or C++ and, in addition, requires extensive knowledge of
        an existing codebase into which the work must fit.""")

    VERYDIFFICULT = DBItem(90, """
        Very Difficult

        This project requires exceptional programming skill and knowledge of
        very low level programming environments, such as assembly language.""")

    EXTREME = DBItem(100, """
        Extreme

        In order to complete this work, detailed knowledge of an existing
        project is required, and in addition the work itself must be done in
        a low-level language like assembler or C on multiple architectures.""")


class BountyStatus(DBEnumeratedType):
    """Bounty Status

    An indicator of the status of a particular bounty. This can be edited by
    the bounty owner or reviewer.
    """

    OPEN = DBItem(1, """
        Open

        This bounty is open. People are still welcome to contact the creator
        or reviewer of the bounty, and submit their work for consideration
        for the bounty.""")

    WITHDRAWN = DBItem(9, """
        Withdrawn

        This bounty has been withdrawn.
        """)

    CLOSED = DBItem(10, """
        Closed

        This bounty is closed. No further submissions will be considered.
        """)


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
        title=_('Status'), vocabulary=BountyStatus,
        default=BountyStatus.OPEN)
    difficulty = Choice(
        title=_('Difficulty'), vocabulary=BountyDifficulty,
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

