# Imports from zope
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


#
# Build Interfaces
#

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

class IBuilder(Interface):
    processor = Attribute("The Builder Processor")
    url = Attribute("The URL to the builder")
    name = Attribute("The Builder Name")
    title = Attribute("The Builder Title")
    description = Attribute("The Builder Description")
    owner = Attribute("The Builder Owner")
    builderok = Attribute("Whether or not the builder is ok")
    failnotes = Attribute("The reason for a builder not being ok")
    trusted = Attribute("Whether not the builder is trusted to build packages under security embargo.")

class IBuildSet(Interface):
    """Interface for BuildSet"""
    def getBuildBySRAndArchtag(sourcepackagereleaseID, archtag):
        """return a build for a SourcePackageRelease and an ArchTag"""
        
class IBuildQueue(Interface):
    """A build queue entry"""
    build = Attribute("The build in question")
    builder = Attribute("The builder building the build")
    created = Attribute("The datetime that the queue entry waw created")
    buildstart = Attribute("The datetime of the last build attempt")
    logtail = Attribute("The current tail of the log of the build")

