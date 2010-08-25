# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""ArchiveArch interfaces."""

__metaclass__ = type

__all__ = [
    'IArchiveArch',
    'IArchiveArchSet',
    ]

from lazr.restful.fields import Reference
from zope.interface import Interface
from zope.schema import Int

from canonical.launchpad import _
from lp.soyuz.interfaces.archive import IArchive
from lp.soyuz.interfaces.processor import IProcessorFamily


class IArchiveArch(Interface):
    """An interface for archive/processor family associations."""

    id = Int(title=_('ID'), required=True, readonly=True)

    archive = Reference(
        title=_("Archive"), schema=IArchive,
        required=True, readonly=True,
        description=_(
            "The archive associated with the processor family at hand."))

    processorfamily = Reference(
        title=_("Processor family"), schema=IProcessorFamily,
        required=True, readonly=True,
        description=_(
            "The processorfamily associated with the archive at hand."))


class IArchiveArchSet(Interface):
    """An interface for sets of archive/processor family associations."""
    def new(archive, processorfamily):
        """Create a new archive/processor family association.

        :param archive: the archive to be associated.
        :param processorfamily: the processor family to be associated.

        :return: a newly created `IArchiveArch`.
        """

    def getByArchive(archive, processorfamily=None):
        """Return associations that match the archive and processor family.

        If no processor family is passed, all associations for 'archive' will
        be returned.

        :param archive: The associated archive.
        :param processorfamily: An optional processor family; if passed only
        associations in which it participates will be considered.

        :return: A (potentially empty) result set of `IArchiveArch` instances.
        """

    def getRestrictedFamilies(archive):
        """All restricted processor families, paired with `ArchiveArch`
        instances if associated with `archive`.

        :return: A sequence containing a (`ProcessorFamily`, `ArchiveArch`)
            2-tuple for each processor family.
            The second value in the tuple will be None if the given `archive`
            is not associated with the `ProcessorFamily` yet.
        """

