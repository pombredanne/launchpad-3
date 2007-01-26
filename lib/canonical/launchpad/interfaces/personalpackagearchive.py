# Copyright 2006 Canonical Ltd.  All rights reserved.

"""PersonalPackageArchive interfaces."""

__metaclass__ = type

__all__ = [
    'IPersonalPackageArchive',
    'IPersonalPackageArchiveSet',
    ]

from zope.interface import Interface, Attribute

from canonical.launchpad import _


class IPersonalPackageArchive(Interface):
    """A PersonalPackageArchive interface"""
    id = Attribute("The archive ID.")

class IPersonalPackageArchiveSet(Interface):
    """Interface for PersonalPackageArchiveSet"""

    title = Attribute('Title')

    def new(person, archive):
        """Create a new personalpackagearchive."""

    def get(ppaid):
        """Return the IPersonalPackageArchive with the given id."""

