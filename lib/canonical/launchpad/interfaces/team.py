# Imports from zope
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

#
# Team Interfaces
#

class IMembership(Interface):
    """Membership for Users"""
    person = Attribute("Owner")
    team = Attribute("Team")
    role= Attribute("Role on Team")
    status= Attribute("Status of this Relation")
    rolename = Attribute("Role Name")
    statusname = Attribute("Status Name")
    
class ITeamParticipation(Interface):
    """Team Participation for Users"""
    person = Attribute("Owner")
    team = Attribute("Team")

#
# Team related Application Interfaces
#

class IDistroTeamApp(Interface):
    """A Distribution Team Tag """
    distribution = Attribute("Distribution")
    team = Attribute("Team")

    def __getitem__(release):
        """retrieve team by release"""

    def __iter__():
        """retrieve an iterator"""

class IDistroReleaseTeamApp(Interface):
    """A DistroRelease People Tag """
    release= Attribute("Release")
    team = Attribute("Team")
