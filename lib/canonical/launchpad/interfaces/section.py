# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Section interfaces."""

__metaclass__ = type

__all__ = [
    'ISection',
    'ISectionSet',
    ]

from zope.interface import Interface, Attribute

class ISection(Interface):
    id = Attribute("The ID")
    name = Attribute("The Section Name")

class ISectionSet(Interface):
    """Interface for SectionSet"""

    def __iter__():
        """Iterate over section."""

    def __getitem__(name):
        """Retrieve a section by name"""

    def get(section_id):
        """Return the ISection with the given section_id."""

    def new(name):
        """Create a new section."""
