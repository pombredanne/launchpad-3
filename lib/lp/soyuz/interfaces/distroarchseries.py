# Copyright 2009-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Distribution architecture series interfaces."""

__metaclass__ = type

__all__ = [
    'IDistroArchSeries',
    'InvalidChrootUploaded',
    'IPocketChroot',
    ]

import httplib

from lazr.restful.declarations import (
    error_status,
    export_as_webservice_entry,
    export_write_operation,
    exported,
    operation_for_version,
    operation_parameters,
    )
from lazr.restful.fields import (
    Reference,
    ReferenceChoice,
    )
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Bytes,
    Int,
    Text,
    TextLine,
    )

from lp import _
from lp.app.validators.name import name_validator
from lp.buildmaster.interfaces.processor import IProcessor
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.role import IHasOwner
from lp.soyuz.interfaces.buildrecords import IHasBuildRecords


@error_status(httplib.BAD_REQUEST)
class InvalidChrootUploaded(Exception):
    """Raised when the sha1sum of an uploaded chroot does not match."""


class IDistroArchSeriesPublic(IHasBuildRecords, IHasOwner):
    """Public attributes for a DistroArchSeries."""

    id = Attribute("Identifier")
    distroseries = exported(
        Reference(
            IDistroSeries,
            title=_("The context distroseries"),
            required=False, readonly=False))
    processor = exported(
        ReferenceChoice(
            title=_("Processor"), required=True, readonly=True,
            vocabulary='Processor', schema=IProcessor))
    architecturetag = exported(
        TextLine(
            title=_("Architecture Tag"),
            description=_(
                "The architecture tag, or short piece of text that "
                "identifies this architecture. All binary packages in the "
                "archive will use this tag in their filename. Please get it "
                "correct. It should really never be changed!"),
            required=True,
            constraint=name_validator),
        exported_as="architecture_tag")
    official = exported(
        Bool(
            title=_("Official Support"),
            description=_(
                "Indicate whether or not this port has official "
                "support from the vendor of the distribution."),
            required=True))
    owner = exported(
        Reference(
            IPerson,
            title=_('The person who registered this port.'),
            required=True))
    package_count = exported(
        Int(
            title=_("Package Count"),
            description=_(
                'A cache of the number of packages published '
                'in the RELEASE pocket of this port.'),
            readonly=False, required=False))
    supports_virtualized = exported(
        Bool(
            title=_("PPA support available"),
            description=_("Indicate whether or not this port has support "
                          "for building PPA packages."),
            readonly=True, required=False))
    enabled = exported(
        Bool(
            title=_("Enabled"),
            description=_(
                "Whether or not this DistroArchSeries is enabled for build "
                "creation and publication."),
            readonly=False, required=False),
        as_of="devel")

    # Joins.
    packages = Attribute('List of binary packages in this port.')

    # Page layouts helpers.
    title = exported(
        TextLine(
            title=_('Title'),
            description=_("The title of this distroarchseries.")))

    displayname = exported(
        TextLine(
            title=_("Display name"),
            description=_("The display name of this distroarchseries.")),
        exported_as="display_name")

    # Other useful bits.
    isNominatedArchIndep = exported(
        Bool(
            title=_("Is Nominated Arch Independent"),
            description=_(
                'True if this distroarchseries is the NominatedArchIndep '
                'one.')),
        exported_as="is_nominated_arch_indep")
    main_archive = exported(
        Reference(
            Interface,  # Really IArchive, circular import fixed below.
            title=_('Main Archive'),
            description=_("The main archive of the distroarchseries.")))
    chroot_url = exported(
        TextLine(
            title=_("Build chroot URL"),
            description=_(
                "The URL to the current build chroot for this "
                "distroarchseries."),
            readonly=True))

    def updatePackageCount():
        """Update the cached binary package count for this distro arch
        series.
        """
    def getPocketChroot():
        """Return the PocketChroot for this distroarchseries and given pocket.
        """

    def getChroot(default=None):
        """Return the Chroot for this distroarchseries.

        It uses getPocketChroot and if not found returns 'default'.
        """

    def addOrUpdateChroot(pocket, chroot):
        """Return the just added or modified PocketChroot."""

    def searchBinaryPackages(text):
        """Search BinaryPackageRelease published in this series for those
        matching the given text."""

    def __getitem__(name):
        """Getter"""

    def getBinaryPackage(name):
        """Return the DistroArchSeriesBinaryPackage with the given name in
        this distro arch series.
        """


class IDistroArchSeriesModerate(Interface):

    @operation_parameters(data=Bytes(), sha1sum=Text())
    @export_write_operation()
    @operation_for_version("devel")
    def setChroot(data, sha1sum):
        """Set the chroot tarball used for builds in this architecture.

        The SHA-1 checksum must match the chroot file.
        """

    @export_write_operation()
    @operation_for_version("devel")
    def removeChroot():
        """Remove the chroot tarball used for builds in this architecture."""


class IDistroArchSeries(IDistroArchSeriesPublic, IDistroArchSeriesModerate):
    """An architecture for a distroseries."""
    export_as_webservice_entry()


class IPocketChroot(Interface):
    """PocketChroot Table Interface"""
    id = Attribute("Identifier")
    distroarchseries = Attribute(
        "The DistroArchSeries this chroot belongs to.")
    pocket = Attribute("The Pocket this chroot is for.")
    chroot = Attribute("The file alias of the chroot.")

    def syncUpdate():
        """Commit changes to DB."""
