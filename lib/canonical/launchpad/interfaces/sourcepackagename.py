# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Source package name interfaces."""

__metaclass__ = type

__all__ = [
    'ISourcePackageName',
    'ISourcePackageNameSet',
    ]

from zope.schema import Int, TextLine
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

from canonical.launchpad.validators.name import valid_name

_ = MessageIDFactory('launchpad')


class ISourcePackageName(Interface):
    """Interface provied by a SourcePackageName.

    This is a tiny table that allows multiple SourcePackage entities to share
    a single name.
    """

    """Name of a SourcePackage"""

    id = Int(title=_("ID"), required=True)
    name = TextLine(title=_("Valid Source package name"),
                    required=True, constraint=valid_name)
    potemplates = Attribute("The list of PO templates that this object has.")
    packagings = Attribute("Everything we know about the packaging of "
        "packages with this source package name.")

    def __unicode__():
        """Return the name"""


class ISourcePackageNameSet(Interface):
    """A set of SourcePackageName."""

    def __getitem__(name):
        """Retrieve a sourcepackagename by name."""

    def __iter__():
        """Iterate over names"""

    def get(sourcepackagenameid):
        """Return a sourcepackagename by its id.

        If the sourcepackagename can't be found a zope.exceptions.NotFoundError
        will be raised.
        """

    def findByName(name):
        """Find sourcepackagenames by its name or part of it"""

    def queryByName(name):
        """Get a sourcepackagename by its name atttribute.

        Returns the matching ISourcePackageName or None.
        """

    def new(name):
        """Create a new source package name."""

    def getOrCreateByName(name):
        """Get a source package name by name, creating it if necessary."""

