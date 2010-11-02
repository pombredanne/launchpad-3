# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for events."""

__metaclass__ = type
__all__ = [
    'IJoinTeamEvent',
    'IKarmaAssignedEvent',
    'IMessageHeldEvent',
    'ITeamInvitationEvent',
    ]

from lazr.lifecycle.interfaces import IObjectCreatedEvent
from zope.component.interfaces import IObjectEvent
from zope.interface import (
    Attribute,
    Interface,
    )


class IJoinTeamEvent(Interface):
    """A person/team joined (or tried to join) a team."""

    person = Attribute("The person/team who joined the team.")
    team = Attribute("The team.")


class ITeamInvitationEvent(Interface):
    """A new person/team has been invited to a team."""

    member = Attribute("The person/team who was invited.")
    team = Attribute("The team.")


class IKarmaAssignedEvent(IObjectEvent):
    """Karma was assigned to a person."""

    karma = Attribute("The Karma object assigned to the person.")


class IMessageHeldEvent(IObjectCreatedEvent):
    """A mailing list message has been held for moderator approval."""

    mailing_list = Attribute('The mailing list the message is held for.')
    message_id = Attribute('The Message-ID of the held message.')
