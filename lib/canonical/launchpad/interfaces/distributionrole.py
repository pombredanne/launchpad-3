# Zope schema imports
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

#
#
#

class IDistributionRole(Interface):
    """A Distribution Role Object"""
    distribution = Attribute("Distribution")
    person = Attribute("Person")
    role = Attribute("Role")
    rolename = Attribute("Rolename")

