# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.app.event.interfaces import IObjectModifiedEvent, IObjectEvent
from zope.interface import Attribute

class ISQLObjectModifiedEvent(IObjectModifiedEvent):
    """An SQLObject has been modified."""

    object_before_modification = Attribute("The object before modification.")
    edited_fields = Attribute(
        "The list of fields that were edited (though not necessarily all "
        "modified, of course.)")
    principal = Attribute("The principal for this event.")

class ISQLObjectToBeModifiedEvent(IObjectEvent):
    """An SQLObject is about to be modified."""

    new_values = Attribute("A dict of fieldname -> newvalue pairs.")
