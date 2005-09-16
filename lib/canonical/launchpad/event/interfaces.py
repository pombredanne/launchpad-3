# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

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
        "The list of fields that were edited (though not necessarily all "
        "modified, of course.)")
    user = Attribute("The user who modified the object.")


class ISQLObjectToBeModifiedEvent(IObjectEvent):
    """An SQLObject is about to be modified."""

    new_values = Attribute("A dict of fieldname -> newvalue pairs.")
    user = Attribute("The user who will modify the object.")


class IJoinTeamRequestEvent(Interface):
    """An user requested to join a team."""

    user = Attribute("The user who requested to join the team.")
    team = Attribute("The team.")
    appurl = Attribute("The base url. (i.e. https://launchpad.ubuntu.com)")

