
# Zope schema imports
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from canonical.launchpad.fields import Title, Summary, Description


class IPackaging(Interface):
    """
    A DOAP Packaging entry. It releates a SourcePackage and Product
    with an packaging type.
    """
    ## XXX cprov 20050204
    ## Field ID is required by SQLobject but not necessary at all
    id = Int(title=_('Packaging entry ID'))
             
    product = Int(title=_('Product'),description=_("""Product ID"""))

    sourcepackage = Choice(title=_('SourcePackage'), required=True,
                           vocabulary='SourcePackage', 
                           description=_("""SourcePackage ID"""))
    

    packaging = Choice(title=_('Packaging'), required=True,
                       vocabulary='Packaging',
                       description=_("""Packaging type."""))
    
class IPackagingUtil(Interface):
    """Utilities to handle Packaging."""
    
    def createPackaging(product, sourcepackage, packaging):
        """Create Packaging entry."""
