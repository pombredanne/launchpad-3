
# Zope schema imports
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

class IProductRelease(Interface):
    """A specific release (i.e. has a version) of a product. For example,
    Mozilla 1.7.2 or Apache 2.0.48."""
    id = Int(title=_('ID'), required=True, readonly=True)
    product = Choice(
        title=_('Product'), required=True, vocabulary='Product')
    datereleased = Datetime(
        title=_('Date Released'), required=True, readonly=True)
    version = TextLine(
        title=_('Version'), required=True, readonly=True)
    title = TextLine(
        title=_('Title'), required=True, readonly=True)
    shortdesc = Text(
        title=_("Short Description"), required=True)
    description = Text(
        title=_("Description"), required=True)
    changelog = Text(
        title=_('Changelog'), required=True)
    ownerID = Int(
        title=_('Owner'), required=True, readonly=True)
    owner = Attribute("The owner's IPerson")
    productseries = Int(title=_('Product Series'), readonly=True)
    
