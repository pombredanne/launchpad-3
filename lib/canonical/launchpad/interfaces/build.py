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
    sourcepackagerelease = Attribute("Sourcepackagerelease reference")

class IBuilder(Interface):
    processor = Attribute("The Builder Processor")
    fqdn = Attribute("The FQDN")
    name = Attribute("The Builder Name")
    title = Attribute("The Builder Title")
    description = Attribute("The Builder Description")
    owner = Attribute("The Builder Owner")

