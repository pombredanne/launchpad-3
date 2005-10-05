# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Build interfaces."""

__metaclass__ = type

__all__ = [
    'IBuild',
    'IBuildSet',
    ]

from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
from zope.schema import Choice, TextLine, Bool

_ = MessageIDFactory('launchpad')

class IBuild(Interface):
    """A Build interface"""
    datecreated = Attribute("Date of BinPackage Creation")
    processor = Attribute("BinaryPackage Processor")
    distroarchrelease = Attribute("The Ditro Arch Release")
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
    title = Attribute("Build Title")
    buildlogURL = Attribute("Librarian Build log path")
    distrorelease = Attribute("Direct parent needed by CanonicalURL")

class IBuildSet(Interface):
    """Interface for BuildSet"""
    def getBuildBySRAndArchtag(sourcepackagereleaseID, archtag):
        """Return a build for a SourcePackageRelease and an ArchTag"""

    def getBuiltForDistroRelease(distrorelease, limit=10):
        """Return build records within a DistroRelease context.

        The results are limited by 'limit'.
        """

    def getBuiltForDistroArchRelease(distroarchrelease, limit=10):
        """Return build records within a DistroArchRelease context.

        The results are limited by 'limit'.
        """
