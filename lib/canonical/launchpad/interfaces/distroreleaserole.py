# Zope schema imports
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

#
#
#

class IDistroReleaseRole(Interface):
    """A Distroreleaserole Object """
    distrorelease= Attribute("Release")
    person = Attribute("Person")
    role = Attribute("Role")
    rolename = Attribute("Rolename")

