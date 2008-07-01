# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

"""Interfaces for events."""

__metaclass__ = type
__all__ = [
    'IJoinTeamEvent',
    'IKarmaAssignedEvent',
    'IMessageHeldEvent',
    'ISQLObjectCreatedEvent',
    'ISQLObjectDeletedEvent',
    'ISQLObjectModifiedEvent',
    'ITeamInvitationEvent',
    ]

from zope.app.event.interfaces import (
    IObjectModifiedEvent, IObjectEvent, IObjectCreatedEvent)
from zope.interface import Interface, Attribute


class ISQLObjectCreatedEvent(IObjectCreatedEvent):
    """An SQLObject has been created."""
    user = Attribute("The user who created the object.")


class ISQLObjectDeletedEvent(IObjectEvent):
    """An SQLObject is being deleted."""
    user = Attribute("The user who is making this change.")


class ISQLObjectModifiedEvent(IObjectModifiedEvent):
    """An SQLObject has been modified."""

    object_before_modification = Attribute("The object before modification.")
    edited_fields = Attribute(
        "The list of fields that were edited. A field name may appear in "
        "this list if it were shown on an edit form, but not actually "
        "changed.")
    user = Attribute("The user who modified the object.")


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


class IMessageHeldEvent(ISQLObjectCreatedEvent):
    """A mailing list message has been held for moderator approval."""

    mailing_list = Attribute('The mailing list the message is held for.')
    message_id = Attribute('The Message-ID of the held message.')
