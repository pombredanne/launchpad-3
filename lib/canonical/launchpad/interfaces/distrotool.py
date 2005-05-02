# Zope schema imports
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

#
#
#

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
