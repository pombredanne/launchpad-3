# Imports from zope
from zope.schema import Int, TextLine
from zope.interface import Interface
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

#
# Interface provied by a SourcePackageName. This is a tiny
# table that allows multiple SourcePackage entities to share
# a single name.
#
class ISourcePackageName(Interface):
    """Name of a SourcePackage"""

    id = Int(title=_("ID"), required=True)
    name = TextLine(title=_("Name"), required=True)

    def __unicode__():
        """Return the name"""


