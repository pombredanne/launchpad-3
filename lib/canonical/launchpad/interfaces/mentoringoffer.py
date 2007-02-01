# Copyright 2005 Canonical Ltd.  All rights reserved.

"""MentoringOffer interfaces."""

__metaclass__ = type

__all__ = [
    'IMentoringOffer',
    ]


from zope.interface import Attribute

from zope.schema import Datetime, Choice

from canonical.launchpad import _
from canonical.launchpad.interfaces import IHasOwner


class IMentoringOffer(IHasOwner):
    """An offer of mentoring help."""

    owner = Choice(title=_('Owner'), required=True, readonly=True,
        vocabulary='ValidPersonOrTeam')
    team = Choice(title=_('Team'), required=True,
        description=_("Working on this item would be good practise for "
            "joining which team?"),
        vocabulary='UserTeamsParticipation')
    date_created = Datetime(
        title=_('Date Created'), required=True, readonly=True)

    # properties
    target = Attribute("The bug or specification for which mentoring is"
        "offered.")


