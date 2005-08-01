# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Binary package name interfaces."""

__metaclass__ = type

__all__ = [
    'IBinaryPackageName',
    'IBinaryPackageNameSet',
    ]

from zope.schema import Int, TextLine
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

from canonical.launchpad.validators.name import valid_name

_ = MessageIDFactory('launchpad')

class IBinaryPackageName(Interface):
    id = Int(title=_('ID'), required=True)

    name = TextLine(title=_('Valid Binary package name'),
                    required=True, constraint=valid_name)

    binarypackages = Attribute('binarypackages')

    def nameSelector(sourcepackage=None, selected=None):
        """Return browser-ready HTML to select a Binary Package Name"""

    def __unicode__():
        """Return the name"""


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

    def new(name):
        """Create a new binary package name."""

    def getOrCreateByName(name):
        """Get a binary package by name, creating it if necessary."""

    def ensure(name):
        """Ensure that the given BinaryPackageName exists, creating it
        if necessary.

        Returns the BinaryPackageName
        """
