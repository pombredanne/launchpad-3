
# Zope schema imports
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from canonical.launchpad.fields import Title, Summary, Description


class IPackaging(Interface):
    """
    A Packaging entry. It relates a SourcePackageName, DistroRelease
    and ProductSeries, with a packaging type. So, for example, we use this
    table to specify that the mozilla-firefox package in hoary is actually a
    primary packaging of firefox 1.0 series releases.
    """
    id = Int(title=_('Packaging ID'))
             
    productseries = Choice(title=_('Product Series'), required=True,
                           vocabulary='ProductSeries',
                           description=_('XXX should limit to this product',
                                         ' series.'))

    sourcepackagename = Choice(title=_("Source Package Name"),
                           required=True, vocabulary='SourcePackageName')

    distrorelease = Choice(title=_("Distribution Release"),
                           required=True, vocabulary='DistroRelease')

    packaging = Choice(title=_('Packaging'), required=True,
                       vocabulary='PackagingType')
    
class IPackagingUtil(Interface):
    """Utilities to handle Packaging."""
    
    def createPackaging(productseries, sourcepackagename,
                        distrorelease, packaging):
        """Create Packaging entry."""
