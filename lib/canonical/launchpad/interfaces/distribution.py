# Zope schema imports
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from canonical.launchpad.fields import Title, Summary, Description
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
    title = Title(title=_("Title"), required=True,
        description=_("The distro's title."))
    summary = Summary(title=_("Summary"), required=True,
        description=_("The distribution summary. A short paragraph"
                      "describing the goals and highlights of the distro."))
    description = Description(title=_("Description"), required=True,
        description=_("The distro's description."))
    domainname = TextLine(title=_("Domain name"), required=True,
        description=_("The distro's domain name."))
    owner = Int(title=_("Owner"), required=True,
        description=_("The distro's owner."))
    
    releases = Attribute("DistroReleases inside this Distributions")
    role_users = Attribute("Roles inside this Distributions")
    
    bugCounter = Attribute("The distro bug counter")

    def traverse(name):
        """Traverse the distribution. Check for special names, and return
        appropriately, otherwise use __getitem__"""

    def __getitem__(name):
        """Returns a DistroRelease that matches name, or raises and
        exception if none exists."""

    def __iter__():
        """Iterate over the distribution releases for this distribution."""

class IDistributionSet(Interface):
    """Interface for DistrosSet"""

    def __iter__():
        """Iterate over distributions."""

    def __getitem__(name):
        """Retrieve a distribution by name"""

    def count():
        """Return the number of distributions in the system."""

class IDistroPackageFinder(Interface):
    """A tool to find packages in a distribution."""

