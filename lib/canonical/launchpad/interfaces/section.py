# Zope schema imports
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

#
#
#

class ISection(Interface):
    name = Attribute("The Section Name")

