# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces for linking between Sprint and a Specification."""

__metaclass__ = type

__all__ = [
    'ISprintSpecification',
    'SprintSpecificationStatus'
    ]

from zope.interface import Interface, Attribute
from zope.schema import Choice, Int, Text, Datetime
from canonical.launchpad import _
from canonical.lazr import DBEnumeratedType, DBItem


class ISprintSpecification(Interface):
    """A link between a Sprint and a Specification."""

    id = Attribute("The ID of this sprint/spec link. We expose this because"
        "there is no uniqueness of spec names across projects and of course "
        "distros, so there is no unique way to identify a sprintspec by "
        "spec name, because multiple specs at a sprint could have the same "
        "name.")
    sprint = Choice(title=_('Sprint'), required=True, readonly=True,
        description=_("Select the meeting or sprint at which you would like "
        "feature to be discussed or implemented. The meeting organisers "
        "will review and approve or decline this request."),
        vocabulary='FutureSprint')
    specification = Int(title=_('Specification'), required=True,
        readonly=True)
    status = Choice(title=_('Agenda Status'), required=True,
        vocabulary='SprintSpecificationStatus')
    whiteboard = Text(title=_('Whiteboard'), required=False,
        description=_(
            "Any reasoning or rationale for your decision. "
            "Your changes will override the current text. Note that "
            "this is purely related to whether this spec is approved for "
            "the agenda of this meeting, not a commentary of "
            "the specification in general."))
    registrant = Choice(title=_('Nominated by'), required=False,
        vocabulary='ValidPersonOrTeam')
    date_created = Datetime(
        title=_('Date nominated'),
        description=_("The date this topic was nominated for the sprint "
        "agenda."))
    decider = Choice(title=_('Decided by'), required=False,
        vocabulary='ValidPersonOrTeam')
    date_decided = Datetime(
        title=_('Date decided'),
        description=_("The date this topic was reviewed and accepted or "
        "declined for the meeting agenda."))

    is_confirmed = Attribute("True if this spec is confirmed for the "
        "agenda of this sprint.")
    is_decided = Attribute('True if this spec has been accepted or '
        'declined for this sprint.')

    def acceptBy(decider):
        """Flag the sprint as being accepted by the decider."""

    def declineBy(decider):
        """Flag the sprint as being declined by the decider."""


class SprintSpecificationStatus(DBEnumeratedType):
    """The current approval status of the spec on this sprint's agenda.

    This enum allows us to know whether or not the meeting admin team has
    agreed to discuss an item.
    """

    ACCEPTED = DBItem(10, """
        Accepted

        The meeting organisers have confirmed this topic for the meeting
        agenda.
        """)

    DECLINED = DBItem(20, """
        Declined

        This spec has been declined from the meeting agenda
        because of a lack of available resources, or uncertainty over
        the specific requirements or outcome desired.
        """)

    PROPOSED = DBItem(30, """
        Proposed

        This spec has been submitted for consideration by the meeting
        organisers. It has not yet been accepted or declined for the
        agenda.
        """)
