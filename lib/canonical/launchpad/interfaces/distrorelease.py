
# Zope schema imports
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


class IDistroRelease(Interface):
    """A Release Object"""
    id = Attribute("The distrorelease's unique number.")
    distribution = Attribute("The release's reference.")
    name= Attribute("The release's name.")
    title = Attribute("The release's title.")
    description = Attribute("The release's description.")
    version = Attribute("The release's version")
    componentes = Attribute("The release componentes.")
    sections = Attribute("The release section.")
    releasestate = Attribute("The release's state.")
    datereleased = Attribute("The datereleased.")
    parentrelease = Attribute("Parent Release")
    owner =Attribute("Owner")
    sourcecount = Attribute("Source Packages Counter")
    binarycount = Attribute("Binary Packages Counter")
    state = Attribute("DistroRelease Status")
    parent = Attribute("DistroRelease Parent")
    displayname = Attribute("Distrorelease Displayname")
    shortdesc = Attribute("Distrorelease Short Description")
    lucilleconfig = Attribute("Lucille Configuration Field")
    bugCounter = Attribute("The distro bug counter")
    role_users = Attribute("Roles inside this Releases")

