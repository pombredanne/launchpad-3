# Imports from zope
from zope.interface import Interface
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

#
#
#

class IBinaryPackageNameSet(Interface):

    def __getitem__(name):
        """Retrieve a binarypackagename by name."""

    def __iter__():
        """Iterate over names"""

    def findByName(name):
        """Find binarypackagenames by its name or part of it"""

    def query(name, distribution=None, distrorelease=None,
              distroarchrelease=None, text=None):
        """Return the binary package names for packages that match the given
        criteria."""

