# Zope schema imports
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

class IDistroReleaseRole(Interface):
    """A Distroreleaserole Object """
    distrorelease= Attribute("Release")
    person = Attribute("Person")
    role = Attribute("Role")
    rolename = Attribute("Rolename")

class IDistributionRole(Interface):
    """A Distribution Role Object"""
    distribution = Attribute("Distribution")
    person = Attribute("Person")
    role = Attribute("Role")
    rolename = Attribute("Rolename")

class IComponent(Interface):
    name = Attribute("The Component Name")

class ISection(Interface):
    name = Attribute("The Section Name")

class IDistroArchRelease(Interface):
    """DistroArchRelease Table Interface"""
    distrorelease = Attribute("DistroRelease")
    processorfamily = Attribute("ProcessorFamily")
    architecturetag = Attribute("ArchitectureTag")
    owner = Attribute("Owner")
 
class IDistroTools(Interface):
    """Interfaces to Tools for Distribution and DistroRelase Manipulation"""

    def createDistro(owner, name, displayname, title,
        summary, description, domain):
        """ Create a Distribution """

    def createDistroRelease(owner, title, distribution, shortdesc, description,
                            version, parent):
        """ Create a DistroRelease """        
    def getDistroRelease():
        """Return All Available DistroReleases"""
