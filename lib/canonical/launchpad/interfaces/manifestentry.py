
# Imports from zope
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

#
# ManifestEntry Related Interfaces
#

class IManifestEntry(Interface):
    """"""
    branch = Attribute("A branch")


