# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Distribution architecture series interfaces."""

__metaclass__ = type

__all__ = [
    'IDistroArchSeries',
    'IDistroArchSeriesSet',
    'IPocketChroot',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Bool, Choice, Int, TextLine

from canonical.launchpad.interfaces.archive import IArchive
from canonical.launchpad.interfaces.distroseries import IDistroSeries
from canonical.launchpad.interfaces.person import IPerson
from canonical.launchpad.interfaces import IHasOwner
from canonical.launchpad import _

from canonical.lazr.fields import Reference
from canonical.lazr.rest.declarations import (
    export_as_webservice_entry, exported)


class IDistroArchSeries(IHasOwner):
    """DistroArchSeries Table Interface"""
    export_as_webservice_entry()

    id = Attribute("Identifier")
    distroseries = exported(
        Reference(
            IDistroSeries,
            title=_("The context distroseries"),
            required=False, readonly=False))
    processorfamily = Choice(
        title=_("Processor Family"),
        required=True, vocabulary='ProcessorFamily')
    architecturetag = exported(
        TextLine(
            title=_("Architecture Tag"),
            description=_(
                "The architecture tag, or short piece of text that "
                "identifies this architecture. All binary packages in the "
                "archive will use this tag in their filename. Please get it "
                "correct. It should really never be changed!"),
            required=True),
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
            required=False))

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
    default_processor = Attribute(
        "Return the DistroArchSeries default processor, by picking the "
        "first processor inside its processorfamily.")
    processors = Attribute(
        "The group of Processors for this DistroArchSeries.processorfamily."
        )
    main_archive = exported(
        Reference(
            IArchive,
            title=_('Main Archive'),
            description=_("The main archive of the distroarchseries.")))

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

    def getReleasedPackages(binary_name, pocket=None, include_pending=False,
                            exclude_pocket=None, archive=None):
        """Get the publishing records for the given binary package name.

        :param: binary_name: should either be a `BinaryPackageName` instance
            or else a string which will be looked up as a `BinaryPackageName`;
        :param: pocket: optional `PackagePublishingPocket` filter, if it is not
            specified, we look in all pockets.
        :param: exclude_pocket: optional negative `PackagePublishingPocket`
            filter, if it is specified exclude results matching that pocket.
        :param: include_pending: optionally return also the pending publication
            records, those packages that will get published in the next publisher
            run (it's only useful when we need to know if a given package is
            known during a publisher run, mostly in pre-upload checks)
        :param: archive: optional IArchive filter, if is not specified, consider
            publication in the main_archives, otherwise respect the given value.

        If the BinaryPackageName cannot be found, NotFoundError will be
        raised.

        :return: a `shortlist` of `IBinaryPackagePublishingHistory` records.
        """

    def __getitem__(name):
        """Getter"""

    def getBinaryPackage(name):
        """Return the DistroArchSeriesBinaryPackage with the given name in
        this distro arch series.
        """


class IDistroArchSeriesSet(Interface):
    """Interface for DistroArchSeriesSet"""

    def __iter__():
        """Iterate over distroarchseriess."""

    def count():
        """Return the number of distroarchseriess in the system."""

    def get(distroarchseries_id):
        """Return the IDistroArchSeries to the given distroarchseries_id."""


class IPocketChroot(Interface):
    """PocketChroot Table Interface"""
    id = Attribute("Identifier")
    distroarchseries = Attribute("The DistroArchSeries this chroot "
                                  "belongs to.")
    pocket = Attribute("The Pocket this chroot is for.")
    chroot = Attribute("The file alias of the chroot.")

    def syncUpdate():
        """Commit changes to DB."""
