# Copyright 2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""MentoringOffer interfaces."""

__metaclass__ = type

__all__ = [
    'ICanBeMentored',
    'IHasMentoringOffers',
    'IMentoringOffer',
    'IMentoringOfferSet',
    ]


from zope.interface import Attribute, Interface

from zope.schema import Datetime, Choice, Bool

from canonical.launchpad import _
from canonical.launchpad.interfaces import IHasOwner


class IMentoringOffer(IHasOwner):
    """An offer of mentoring help."""

    owner = Choice(title=_('Owner'), required=True, readonly=True,
        vocabulary='ValidPerson')
    team = Choice(title=_('Team'), required=True,
        vocabulary='UserTeamsParticipation')
    date_created = Datetime(
        title=_('Date Created'), required=True, readonly=True)
    subscription_request = Bool(title=_('Email me about this'),
        required=True, description=_(
            "Subscribe me to this item so that I get emailed whenever "
            "the status changes or somebody comments. If you are already "
            "subscribed, then leaving this box clear will not "
            "unsubscribe you."))


    # other attributes we don't need to set through a form
    bug = Attribute('A bug, if that is the target, or None')
    specification = Attribute('A blueprint, if that is the target, or None')
    # properties
    target = Attribute("The bug or specification for which mentoring is"
        "offered.")


class IHasMentoringOffers(Interface):
    """Used for objects which have mentoring offers."""

    mentoring_offers = Attribute(
        "The list of mentoring offers related to this object.")


class ICanBeMentored(IHasMentoringOffers):
    """Used for objects which can have mentoring offered or retracted."""

    def canMentor(user):
        """True if this user could now offer mentoring on this piece of
        work. Will be negative if the user is already offering mentoring, or
        if the work is complete, for example.
        """

    def isMentor(user):
        """True if the user is offering mentoring for this piece of work."""

    def offerMentoring(user, team):
        """Record that the user is willing to mentor anyone who is trying to
        do this work.
        """

    def retractMentoring(user):
        """Remove the offer of mentoring for this work by this user."""


class IMentoringOfferSet(IHasMentoringOffers):
    """An object which gives us an overview of mentorship in Launchpad."""

    displayname = Attribute('Display name')
    title = Attribute('Title')

    recent_completed_mentorships = Attribute(
        'Mentorships offered in the past year for which the task (bug or '
        'blueprint) has since been completed.')

