# Imports from zope
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


#
# Wiki Interfaces
#

class IWikiName(Interface):
    """Wiki for Users"""
    person = Attribute("Owner")
    wiki = Attribute("wiki host")
    wikiname = Attribute("wikiname for user")

