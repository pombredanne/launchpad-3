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
    distrorelease = Attribute("Direct parent needed by CanonicalURL")

class IBuildSet(Interface):
    """Interface for BuildSet"""

    def getBuildBySRAndArchtag(sourcepackagereleaseID, archtag):
        """Return a build for a SourcePackageRelease and an ArchTag"""


class IHasBuildRecords(Interface):
    """An Object that has build records"""

    def getBuildRecords(status=None, limit=10):
        """Return build records owned by the object.

        The optional 'status' argument selects build records in a specific
        state. If the 'status' argument is omitted, it returns the "worked"
        entries. A "worked" entry is one that has been touched by a builder.
        That is, where 'builder is not NULL'.

        At most 'limit' results are returned.
        """
