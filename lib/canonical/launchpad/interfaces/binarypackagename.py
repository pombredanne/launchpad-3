# Imports from zope
from zope.schema import Int, TextLine
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

#
#
#

class IBinaryPackageName(Interface):
    id = Int(title=_('ID'), required=True)
    name = TextLine(title=_('Name'), required=True)
    binarypackages = Attribute('binarypackages')

    def nameSelector(sourcepackage=None, selected=None):
        """Return browser-ready HTML to select a Binary Package Name"""

    def __unicode__():
        """Return the name"""

