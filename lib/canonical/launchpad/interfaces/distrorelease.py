
# Zope schema imports
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from canonical.launchpad.fields import Title, Summary, Description
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


class IDistroRelease(Interface):
    """A Release Object"""
    id = Attribute("The distrorelease's unique number.")
    name = TextLine(title=_("Name"), required=True,
        description=_("The name of this distribution release."))
    displayname = TextLine(title=_("Display name"), required=True,
        description=_("The release's displayname."))
    title = Title(title=_("Title"), required=True,
        description=_("""The title of this release. It should be distinctive 
                      and designed to look good at the top of a page."""))
    shortdesc = Summary(title=_("Summary"), required=True,
        description=_("A brief summary of the highlights of this release. "
                      "It should be no longer than a single paragraph, up "
                      "to 200 words."))
    description = Description(title=_("Description"), required=True,
        description=_("A detailed description of this release, with "
                      "information on the architectures covered, the "
                      "availability of security updates and any other "
                      "relevant information."))
    version = TextLine(title=_("Version"), required=True,
        description=_("The version string for this release."))
    distribution = Int(title=_("Distribution"), required=True,
        description=_("The distribution for which this is a release."))
    componentes = Attribute("The release componentes.")
    sections = Attribute("The release section.")
    releasestate = Attribute("The release's state.")
    datereleased = Attribute("The datereleased.")
    parentrelease = Attribute("Parent Release")
    owner =Attribute("Owner")
    state = Attribute("DistroRelease Status")
    parent = Attribute("DistroRelease Parent")
    lucilleconfig = Attribute("Lucille Configuration Field")
    role_users = Attribute("Roles inside this Releases")
    bugCounter = Attribute("The distro bug counter")
    sourcecount = Attribute("Source Packages Counter")
    binarycount = Attribute("Binary Packages Counter")
    architectures = Attribute("The Architecture-specific Releases")

    def getBugSourceRelease():
        """ xxx """

    def architecturecount():
        """Return the number of architectures in this release."""

#    def getSourceByName(name):
#        """Return the latest source package of this name uploaded to this
#        distro release."""

    def __getitem__(arch):
        """Return a Set of Binary Packages in this distroarchrelease."""

    def findSourcesByName(name):
        """Return an iterator over source packages with a name that matches
        this one."""

    def findBinariesByName(name):
        """Return an iterator over binary packages with a name that matches
        this one."""
