# Zope schema imports
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


class IDistribution(Interface):
    """A Distribution Object"""
    id = Attribute("The distro's unique number.")
    name = TextLine(title=_("Name"), description=_("""(The distro's
        name."""), required=True)
    displayname = TextLine(title=_("Display Name"), required=True,
        description=_("The displayable name of the distribution."))
    title = TextLine(title=_("Title"), required=True,
        description=_("The distro's title."))
    summary = Text(title=_("Summary"), required=True,
        description=_("The distribution summary. A short paragraph"
                      "describing the goals and highlights of the distro."))
    description = Text(title=_("Description"), required=True,
        description=_("The distro's description."))
    domainname = TextLine(title=_("Domain name"), required=True,
        description=_("The distro's domain name."))
    owner = Int(title=_("Owner"), required=True,
        description=_("The distro's owner."))
    
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

    def __iter__(self):
        """Iterate over distributions."""

    def __getitem__(name):
        """Retrieve a distribution by name"""

    def count():
        """Return the number of distributions in the system."""

