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
    name = TextLine(
        title=_("Name"),
        description=_("The distro's name."), required=True)
    displayname = TextLine(
        title=_("Display Name"),
        description=_("The displayable name of the distribution."),
        required=True)
    title = Title(
        title=_("Title"),
        description=_("The distro's title."), required=True)
    summary = Summary(
        title=_("Summary"),
        description=_(
            "The distribution summary. A short paragraph"
            "describing the goals and highlights of the distro."),
        required=True)
    description = Description(
        title=_("Description"),
        description=_("The distro's description."),
        required=True)
    domainname = TextLine(
        title=_("Domain name"),
        description=_("The distro's domain name."), required=True)
    owner = Int(
        title=_("Owner"),
        description=_("The distro's owner."), required=True)
    releases = Attribute("DistroReleases inside this Distributions")
    bounties = Attribute(_("The bounties that are related to this distro."))
    bugtasks = Attribute("The bug tasks filed in this distro.")
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

    title = Attribute('Title')

    def __iter__():
        """Iterate over distributions."""

    def __getitem__(name):
        """Retrieve a distribution by name"""

    def count():
        """Return the number of distributions in the system."""

    def get(distributionid):
        """Return the IDistribution with the given distributionid."""

class IDistroPackageFinder(Interface):
    """A tool to find packages in a distribution."""

