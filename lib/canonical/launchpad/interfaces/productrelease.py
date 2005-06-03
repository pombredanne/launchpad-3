
# Zope schema imports
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

class IProductReleaseSet(Interface):
    """Auxiliar class for ProductRelease handling.""" 

    def new(version, owner, productseries, title=None, shortdesc=None,
            description=None, changelog=None):
        """Create a new ProductRelease"""


class IProductRelease(Interface):
    """A specific release (i.e. has a version) of a product. For example,
    Mozilla 1.7.2 or Apache 2.0.48."""
    id = Int(title=_('ID'), required=True, readonly=True)
    datereleased = Datetime(title=_('Date Released'), required=True,
                            readonly=True)
    version = TextLine(title=_('Version'), required=True, readonly=True)
    owner = Int(title=_('Owner'), required=True, readonly=True)
    productseries = Choice(title=_('ProductSeries'), required=True,
                           vocabulary='FilteredProductSeries')
    title = TextLine(title=_('Title'), required=False)
    summary = Text(title=_("Summary"), required=False)
    description = Text(title=_("Description"), required=False)
    changelog = Text(title=_('Changelog'), required=False)

    displayname = Attribute(_('Constructed displayname for a productrelease.'))
    manifest = Attribute(_('Manifest Information.'))
    product = Attribute(_('Retrive Product Instance from ProductSeries.'))
    files = Attribute(_('Iterable of product release files.'))
    potemplates = Attribute(
        _("Return an iterator over this productrelease's PO templates."))
    potemplatecount = Attribute(_("The number of POTemplates for this "
                        "ProductRelease."))

