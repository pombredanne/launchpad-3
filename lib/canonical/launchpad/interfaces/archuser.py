# Imports from zope
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


#
# Arch users Interfaces
#

class IArchUserID(Interface):
    """ARCH specific user ID """
    person = Attribute("Owner")
    archuserid = Attribute("ARCH user ID")

