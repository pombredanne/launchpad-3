# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Distribution architecture release interfaces."""

__metaclass__ = type

__all__ = [
    'IDistroArchRelease',
    'IDistroArchReleaseSet',
    'IPocketChroot',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Bool, Choice, Int, TextLine

from canonical.launchpad.interfaces import IHasOwner
from canonical.launchpad import _

class IDistroArchRelease(IHasOwner):
    """DistroArchRelease Table Interface"""
    id = Attribute("Identifier")
    distrorelease = Attribute("DistroRelease")
    processorfamily = Choice(title=_("Processor Family"),
        required=True, vocabulary='ProcessorFamily')
    architecturetag = TextLine(title=_("Architecture Tag"),
        description=_("The architecture tag, or short piece of text that "
        "identifies this architecture. All binary packages in the archive "
        "will use this tag in their filename. Please get it correct. It "
        "should really never be changed!"), required=True)
    official = Bool(title=_("Official Support"),
        description=_("Indicate whether or not this port has official "
        "support from the vendor of the distribution."), required=True)
    owner = Int(title=_('The person who registered this port.'),
        required=True)
    package_count = Attribute('A cache of the number of packages published '
        'in the RELEASE pocket of this port.')

    #joins
    packages = Attribute('List of binary packages in this port.')

    # for page layouts etc
    title = Attribute('Title')
    displayname = Attribute('Display name')

    # useful attributes
    isNominatedArchIndep = Attribute(
        'True if this distroarchrelease is the NominatedArchIndep one.')

    distribution = Attribute("The distribution of the package.")
    default_processor = Attribute(
        "Return the DistroArchRelease default processor, by picking the "
        "first processor inside its processorfamily.")
    processors = Attribute(
        "The group of Processors for this Distroarchrelease.processorfamily."
        )
    main_archive = Attribute('Main Archive')

    def updatePackageCount():
        """Update the cached binary package count for this distro arch
        release.
        """
    def getPocketChroot(pocket=None):
        """Return the PocketChroot for this distroarchrelease and given pocket.

        The pocket defaults to the RELEASE pocket.
        """

    def getChroot(pocket=None, default=None):
        """Return the Chroot for this distroarchrelease and given pocket.

        It uses getPocketChroot and if not found returns 'default'.
        """

    def addOrUpdateChroot(pocket, chroot):
        """Return the just added or modified PocketChroot."""

    def searchBinaryPackages(text):
        """Search BinaryPackageRelease published in this release for those
        matching the given text."""

    def getReleasedPackages(binary_name, pocket=None, include_pending=False,
                            exclude_pocket=None):
        """Get the publishing records for the given binary package name.

        The 'name' passed in should either be a BinaryPackageName instance
        or else a string which will be looked up as a BinaryPackageName.
        If the BinaryPackageName cannot be found, NotFoundError will be
        raised.

        If pocket is not specified, we look in all pockets.

        if exclude pocket is specified exclude results matching that pocket.

        If 'include_pending' is True, we return also the pending publication
        records, those packages that will get published in the next publisher
        run (it's only useful when we need to know if a given package is
        known during a publisher run, mostly in pre-upload checks)
        """

    def __getitem__(name):
        """Getter"""

    def getBinaryPackage(name):
        """Return the DistroArchReleaseBinaryPackage with the given name in
        this distro arch release.
        """

    def findDepCandidateByName(name):
        """Return the last published binarypackage by given name.

        Return the PublishedPackage record by binarypackagename or None if
        not found.
        """


class IDistroArchReleaseSet(Interface):
    """Interface for DistroArchReleaseSet"""

    def __iter__():
        """Iterate over distroarchreleases."""

    def count():
        """Return the number of distroarchreleases in the system."""

    def get(distroarchrelease_id):
        """Return the IDistroArchRelease to the given distroarchrelease_id."""


class IPocketChroot(Interface):
    """PocketChroot Table Interface"""
    id = Attribute("Identifier")
    distroarchrelease = Attribute("The DistroArchRelease this chroot "
                                  "belongs to.")
    pocket = Attribute("The Pocket this chroot is for.")
    chroot = Attribute("The file alias of the chroot.")

    def syncUpdate():
        """Commit changes to DB."""
