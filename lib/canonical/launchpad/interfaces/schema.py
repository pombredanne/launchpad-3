# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Schema interfaces."""

__metaclass__ = type

__all__ = [
    'ISchemaSet',
    'ISchema',
    'ILabel',
    ]

from zope.interface import Interface, Attribute

class ISchemaSet(Interface):
    """The collection of schemas."""

    def __getitem__(name):
        """Get a schema by its name."""

    def keys():
        """Return an iterator over the schemas names."""


class ISchema(Interface):
    """A Schema."""

    id = Attribute("The id of this schema.")

    owner = Attribute("The Person who owns this schema.")

    name = Attribute("The name of this schema.")

    title = Attribute("The title of this schema.")

    description = Attribute("The description of this schema.")

    def labels():
        """Return an iterator over all labels associated with this schema."""

    def label(name):
        """Returns the label with the given name."""


class ILabel(Interface):
    """A Label."""

    schema = Attribute("The Schema associated with this label.")

    name = Attribute("The name of this schema.")

    title = Attribute("The title of this schema.")

    description = Attribute("The description of this schema.")

    def persons():
        """Returns an iterator over all persons associated with this Label."""


