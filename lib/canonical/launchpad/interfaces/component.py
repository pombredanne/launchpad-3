# Zope schema imports
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

#
#
#

class IComponent(Interface):
    name = Attribute("The Component Name")

