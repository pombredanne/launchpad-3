# Imports from zope
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


#
# IRC Interfaces
#

class IIrcID(Interface):
    """Wiki for Users"""
    person = Attribute("Owner")
    network = Attribute("IRC host")
    nickname = Attribute("nickname for user")

