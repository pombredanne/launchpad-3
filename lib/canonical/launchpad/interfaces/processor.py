# Imports from zope
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

#
# Processor interfaces
#

class IProcessor(Interface):
    """The SQLObject Processor Interface"""
    family = Attribute("The Processor Family Reference")
    name = Attribute("The Processor Name")
    title = Attribute("The Processor Title")
    description = Attribute("The Processor Description")
    owner = Attribute("The Processor Owner")
    
class IProcessorfamily(Interface):
    """The SQLObject Processorfamily Interface"""
    name = Attribute("The Processor Family Name")
    title = Attribute("The Processor Family Title")
    description = Attribute("The Processor Name Description")
    owner = Attribute("The Processor Family Owner")

