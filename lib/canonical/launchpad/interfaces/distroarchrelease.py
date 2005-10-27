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
from zope.i18nmessageid import MessageIDFactory

from canonical.launchpad.interfaces import IHasOwner

_ = MessageIDFactory('launchpad')

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

    def updatePackageCount():
        """Update the cached binary package count for this distro arch
        release.
        """

    def getChroot(pocket=None, default=None):
        """Return the librarian file alias of the chroot for a given Pocket.

        The pocket defaults to the RELEASE pocket and if not found returns
        'default'.
        """

    def searchBinaryPackages(text):
        """Search BinaryPackageRelease published in this release for those
        matching the given text."""

    def getReleasedPackages(name, pocket=None):
        """Get the publishing records for the given binary package name.

        The 'name' passed in should either be a BinaryPackageName instance
        or else a string which will be looked up as a BinaryPackageName.

        If pocket is not specified, we look in all pockets.
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

    distroarchrelease = Attribute("The DistroArchRelease this chroot "
                                  "belongs to.")
    pocket = Attribute("The Pocket this chroot is for.")
    chroot = Attribute("The file alias of the chroot.")

