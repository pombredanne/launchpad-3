# Imports from zope
from zope.interface import Interface
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

#
#
#

class IBinaryPackageNameSet(Interface):

    def __getitem__():
        """Return the packagename that matches the given name text"""

    def query(name, distribution=None, distrorelease=None,
              distroarchrelease=None, text=None):
        """Return the binary package names for packages that match the given
        criteria."""

