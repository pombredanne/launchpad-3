# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Component interfaces."""

__metaclass__ = type

__all__ = [
    'IComponent',
    'IComponentSet'
    ]

from zope.interface import Interface, Attribute

class IComponent(Interface):
    id = Attribute("The ID")
    name = Attribute("The Component Name")


class IComponentSet(Interface):
    """Interface for ComponentSet"""

    def __iter__():
        """Iterate over components."""

    def __getitem__(name):
        """Retrieve a component by name"""

    def get(component_id):
        """Return the IComponent with the given component_id."""

    def new(name):
        """Create a new component."""

