# Copyright 2005 Canonical Ltd.  All rights reserved.

"""MentoringOffer interfaces."""

__metaclass__ = type

__all__ = [
    'IHasMentoringOffers',
    'IMentoringOffer',
    'IMentorshipManager',
    ]


from zope.interface import Attribute, Interface

from zope.schema import Datetime, Choice, Bool

from canonical.launchpad import _
from canonical.launchpad.interfaces import IHasOwner


class IMentoringOffer(IHasOwner):
    """An offer of mentoring help."""

    owner = Choice(title=_('Owner'), required=True, readonly=True,
        vocabulary='ValidPersonOrTeam')
    team = Choice(title=_('Team'), required=True,
        vocabulary='UserTeamsParticipation')
    date_created = Datetime(
        title=_('Date Created'), required=True, readonly=True)

    # properties
    target = Attribute("The bug or specification for which mentoring is"
        "offered.")


class IHasMentoringOffers(Interface):
    """Used for objects which have mentoring offers."""

    mentoring_offers = Attribute(
        "The list of mentoring offers related to this object.")


class IMentorshipManager(IHasMentoringOffers):
    """An object which gives us an overview of mentorship in Launchpad."""

    displayname = Attribute('Display name')
    title = Attribute('Title')


