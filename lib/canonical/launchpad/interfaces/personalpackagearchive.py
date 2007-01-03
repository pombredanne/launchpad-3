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
    id = Attribute("The personal package archive ID.")
    archive = Attribute("The archive for this PPA")
    person = Attribute("The person related with this PPA.(owner)")

    def getPubConfig(distribution):
        """Return an overridden Publisher Configuration instance.

        The original publisher configuration based on the distribution is
        modified according local context, it basically fixes the archive
        paths to cope with PPA publication workflow.
        """

class IPersonalPackageArchiveSet(Interface):
    """Interface for PersonalPackageArchiveSet"""

    title = Attribute('Title')

    def new(person, archive):
        """Create a new personalpackagearchive."""

    def get(ppaid):
        """Return the IPersonalPackageArchive with the given id."""

    def __iter__():
        """Iterates over existent PersonalPackageArchives."""
