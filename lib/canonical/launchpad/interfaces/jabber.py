#Imports from zope
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

#
# Jabber Interfaces
#

class IJabberID(Interface):
    """Jabber specific user ID """
    person = Attribute("Owner")
    jabberid = Attribute("Jabber user ID")

