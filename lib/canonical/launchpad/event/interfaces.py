from zope.app.event.interfaces import IObjectModifiedEvent
from zope.interface import Attribute

class ISQLObjectModifiedEvent(IObjectModifiedEvent):
    """An SQLObject has been modified."""

    object_before_modification = Attribute("The object before it was modified.")
    edited_fields = Attribute("""\
        The list of fields that were edited (though not necessarily all
        modified, of course.)""")
    principal = Attribute("The principal for this event.")
