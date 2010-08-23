# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Source package name interfaces."""

__metaclass__ = type

__all__ = [
    'ISourcePackageName',
    'ISourcePackageNameSet',
    'NoSuchSourcePackageName',
    ]

from lazr.restful.declarations import webservice_error
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Int,
    TextLine,
    )

from canonical.launchpad import _
from canonical.launchpad.validators.name import name_validator
from lp.app.errors import NameLookupFailed


class ISourcePackageName(Interface):
    """Interface provied by a SourcePackageName.

    This is a tiny table that allows multiple SourcePackage entities to share
    a single name.
    """
    id = Int(title=_("ID"), required=True)
    name = TextLine(title=_("Valid Source package name"),
                    required=True, constraint=name_validator)
    potemplates = Attribute("The list of PO templates that this object has.")
    packagings = Attribute("Everything we know about the packaging of "
        "packages with this source package name.")

    def __unicode__():
        """Return the name"""


class ISourcePackageNameSet(Interface):
    """A set of SourcePackageName."""

    def __getitem__(name):
        """Retrieve a sourcepackagename by name."""

    def get(sourcepackagenameid):
        """Return a sourcepackagename by its id.

        If the sourcepackagename can't be found a NotFoundError will be raised.
        """

    def getAll():
        """return an iselectresults representing all package names"""

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


class NoSuchSourcePackageName(NameLookupFailed):
    """Raised when we can't find a particular sourcepackagename."""
    webservice_error(400)
    _message_prefix = "No such source package"
