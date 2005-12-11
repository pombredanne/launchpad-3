# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Build interfaces."""

__metaclass__ = type

__all__ = [
    'IBuild',
    'IBuildSet',
    'IHasBuildRecords'
    ]

from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
from zope.schema import Choice, TextLine, Bool

_ = MessageIDFactory('launchpad')

class IBuild(Interface):
    """A Build interface"""
    id = Attribute("The build ID.")
    datecreated = Attribute("Date of BinPackage Creation")
    processor = Attribute("BinaryPackage Processor")
    distroarchrelease = Attribute("The Distro Arch Release")
    buildstate = Attribute("BinaryBuild State")
    datebuilt = Attribute("Binary Date of Built")
    buildduration = Attribute("Build Duration Interval")
    buildlog = Attribute("The Build LOG Referency")
    builder = Attribute("The Builder")
    gpgsigningkey = Attribute("GPG Signing Key")
    changes = Attribute("The Build Changes")
    component = Attribute("The BinaryPackage Component")
    section = Attribute("The BinaryPackage Section")
    sourcepackagerelease = Attribute("SourcePackageRelease reference")
    distrorelease = Attribute("Direct parent needed by CanonicalURL")
    buildqueue_record = Attribute("Corespondent BuildQueue record")

    title = Attribute("Build Title")

    # useful properties
    build_icon = Attribute("Return the icon url correspondent to buildstate.")
    distribution = Attribute("Shortcut for its distribution.")
    distributionsourcepackagerelease = Attribute("The page showing the "
        "details for this sourcepackagerelease in this distribution.")
    binarypackages = Attribute("A list of binary packages that resulted "
        "from this build.")

    def __getitem__(name):
        """Mapped to getBinaryPackageRelease."""

    def getBinaryPackageRelease(name):
        """Return the binary package from this build with the given name, or
        raise IndexError if no such package exists.
        """



    def createBinaryPackageRelease(binarypackagename, version,
                                   summary, description,
                                   binpackageformat, component,
                                   section, priority, shlibdeps,
                                   depends, recommends, suggests,
                                   conflicts, replaces, provides,
                                   essential, installedsize,
                                   copyright, licence,
                                   architecturespecific):
        """Create a binary package release with the provided args, attached
        to this specific build.
        """

    def createBuildQueueEntry():
        """Create a BuildQueue entry for this build record."""

class IBuildSet(Interface):
    """Interface for BuildSet"""

    def getBuildBySRAndArchtag(sourcepackagereleaseID, archtag):
        """Return a build for a SourcePackageRelease and an ArchTag"""

    def getByBuildID(id):
        """Return the exact build specified.

        id is the numeric ID of the build record in the database.
        I.E. getUtility(IBuildSet).getByBuildID(foo).id == foo
        """

    def getPendingBuildsForArchSet(archrelease):
        """Return all pending build records within a group of ArchReleases

        Pending means that buildstatus is NEEDSBUILDING.
        """
    def getBuildsForBuilder(builder_id, status=None):
        """Return build records touched by a builder.

        If status is provided, only builders with that status will
        be returned.
        """

    def get_builds_by_arch_ids(arch_ids, status=None):
        """Retrieve Build Records for a given arch_ids list.

        Optionally, for a given status, if status is ommited return all
        records.
        """

class IHasBuildRecords(Interface):
    """An Object that has build records"""

    def getBuildRecords(status=None):
        """Return build records owned by the object.

        The optional 'status' argument selects build records in a specific
        state.
        """
