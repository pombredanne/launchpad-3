# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Archive interfaces."""

__metaclass__ = type

__all__ = [
    'IArchive',
    'IArchiveSet',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Text

from canonical.launchpad import _
from canonical.launchpad.validators.name import name_validator


class IArchive(Interface):
    """An Archive interface"""

    id = Attribute("The archive ID.")

    name = Text(
        title=_('Name'), required=True, readonly=False,
        constraint=name_validator,
        description=_(
        "A short unique name, beginning with a lower-case "
        "letter or number, and containing only letters, "
        "numbers, dots, hyphens, or plus signs."))

    owner = Attribute("The owner of the archive, or None for the main "
                      "archive of a distribution")

    def getPubConfig(distribution):
        """Return an overridden Publisher Configuration instance.

        The original publisher configuration based on the distribution is
        modified according local context, it basically fixes the archive
        paths to cope with personal archives publication workflow.
        """


class IArchiveSet(Interface):
    """Interface for ArchiveSet"""

    title = Attribute('Title')

    def new(name, owner=None):
        """Create a new archive."""

    def get(archive_id):
        """Return the IArchive with the given archive_id."""

    def getAllPPAs():
        """Return all existent personal archives."""

    def __iter__():
        """Iterates over existent archives, including the main_archives."""
