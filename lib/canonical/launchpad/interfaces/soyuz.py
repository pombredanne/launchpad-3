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

class IComponent(Interface):
    name = Attribute("The Component Name")

class ISection(Interface):
    name = Attribute("The Section Name")

class IDistributions(Interface):
    """Root object for collection of Distributions"""
    entries = Attribute('number of distributions')
    
    def __getitem__(name):
        """retrieve distribution by name"""

    def distributions():
        """retrieve all Distribution"""

    def new(name, title, description, url):
        """Creates a new distribution with the given name.

        Returns that project.
        """
    
class IDistroApp(Interface):
    distribution = Attribute("Distribution")
    releases = Attribute("Distribution releases")
    enable_releases = Attribute("Enable Distribution releases Features")
    
    def getReleaseContainer(name):
        """Returns an associated IReleaseContainer"""


class IDistroReleasesApp(Interface):
    """Root object for collection of Releases"""
    distribution = Attribute("distribution")

    def __getitem__(name):
        """retrieve distribution by name"""

    def releases():
        """retrieve all projects"""

    def __iter__():
        """retrieve an iterator"""

    def new(name, title, description, url):
        """Creates a new distribution with the given name.

        Returns that project.
        """

class IDistroReleaseApp(Interface):
    """A Release Proxy """
    release = Attribute("Release")
    roles = Attribute("Release Roles")

    def bugSourcePackages(distrorelease):
        """Get SourcePackages in a DistroRelease with BugAssignement"""

    def findSourcesByName(name):
        """Returns The Release SourcePackages by name"""

    def findBinariesByName(name):
        """Returns The Release BianriesPackages by name"""

class IDistroArchRelease(Interface):
    """DistroArchRelease Table Interface"""
    distrorelease = Attribute("DistroRelease")
    processorfamily = Attribute("ProcessorFamily")
    architecturetag = Attribute("ArchitectureTag")
    owner = Attribute("Owner")
 
class IDistroTools(Interface):
    """Interfaces to Tools for Distribution and DistroRelase Manipulation"""

    def createDistro(owner, title, description, domain):
        """ Create a Distribution """

    def createDistroRelease(owner, title, distribution, shortdesc, description,
                            version, parent):
        """ Create a DistroRelease """        
    def getDistroRelease():
        """Return All Available DistroReleases"""
