# Zope schema imports
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


class IDistribution(Interface):
    """A Distribution Object"""
    id = Attribute("The distro's unique number.")
    name = Attribute("The distro's name.")
    title = Attribute("The distro's title.")
    description = Attribute("The distro's description.")
    domainname = Attribute("The distro's domain name.")
    owner = Attribute("The distro's owner.")
    releases = Attribute("DistroReleases inside this Distributions")
    role_users = Attribute("Roles inside this Distributions")
    
    bugCounter = Attribute("The distro bug counter")

    def getRelease(name):
        """Returns an Release that matchs name"""

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

class IDistributionSet(Interface):
    """Interface for DistrosSet"""

    def getDistros():
        """Returns all distributions available on the Database"""

    def getDistrosCounter():
        """Returns the number of Distributions available"""

    def getDistribution(name):
        """Returns a Distribution with name=name"""

