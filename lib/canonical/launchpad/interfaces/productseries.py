

# Zope schema imports
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

class IProductSeries(Interface):
    """A series of releases. For example "2.0" or "1.3" or "dev"."""
    # field names
    product = Choice( title=_('Product'), required=True,
                      vocabulary='Product')
    name = Text(title=_('Name'), required=True)
    displayname = Text( title=_('Display Name'), required=True)
    shortdesc = Text(title=_("Short Description"), required=True)
    # convenient joins
    releases = Attribute(_("An iterator over the releases in this \
                                  Series."))
    
class IProductSeriesSet(Interface):
    """A set of ProductSeries objects. Note that it can be restricted by
    initialising it with a product, in which case it iterates over only the
    Product Release Series' for that Product."""

    def __init__(self, product=None):
        """Initialise the ProductSeriesSet with an optional Product."""

    def __iter__(self):
        """Return an interator over the ProductSeries', constrained by
        self.product if the ProductSeries was initialised that way."""

    def __getitem__(self, name):
        """Return a specific ProductSeries, by name, constrained by the
        self.product. For __getitem__, a self.product is absolutely
        required, as ProductSeries names are only unique within the Product
        they cover."""

