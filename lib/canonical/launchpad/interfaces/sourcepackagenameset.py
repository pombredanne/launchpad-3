# Imports from zope
from zope.interface import Interface
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

#
#
#

class ISourcePackageNameSet(Interface):
    """A set of SourcePackageName."""

    def __getitem__(name):
        """Retrieve a sourcepackage by name."""

    def __iter__():
        """Iterate over names"""

    def get(sourcepackagenameid):
        """Return a sourcepackagename by its id.

        If the sourcepackagename can't be found a zope.exceptions.NotFoundError
        will be raised.
        """

