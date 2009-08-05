# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Binary package name interfaces."""

__metaclass__ = type

__all__ = [
    'IBinaryPackageName',
    'IBinaryAndSourcePackageName',
    'IBinaryPackageNameSet',
    ]

from zope.schema import Int, TextLine
from zope.interface import Interface, Attribute

from canonical.launchpad import _
from canonical.launchpad.validators.name import name_validator


class IBinaryPackageName(Interface):
    id = Int(title=_('ID'), required=True)

    name = TextLine(title=_('Valid Binary package name'),
                    required=True, constraint=name_validator)

    binarypackages = Attribute('binarypackages')

    def nameSelector(sourcepackage=None, selected=None):
        """Return browser-ready HTML to select a Binary Package Name"""

    def __unicode__():
        """Return the name"""


class IBinaryPackageNameSet(Interface):

    def __getitem__(name):
        """Retrieve a binarypackagename by name."""

    def getAll():
        """return an iselectresults representing all package names"""

    def findByName(name):
        """Find binarypackagenames by its name or part of it"""

    def queryByName(name):
        """Return a binary package name.

        If there is no matching binary package name, return None.
        """

    def new(name):
        """Create a new binary package name."""

    def getOrCreateByName(name):
        """Get a binary package by name, creating it if necessary."""

    def ensure(name):
        """Ensure that the given BinaryPackageName exists, creating it
        if necessary.

        Returns the BinaryPackageName
        """

    def getNotNewByNames(name_ids, distroseries, archive_ids):
        """Return `BinaryPackageName`s that are already published.

        For the `BinaryPackageName` ids specified, return a (possible)
        subset where they are published, thus excluding "new" records.

        :param ids: A sequence of IDs of `BinaryPackageName`s.
        :param distroseries: The context `DistroSeries` for the publications.
        :param archive_ids: The context `Archive` IDs for the publications.
        """


class IBinaryAndSourcePackageName(Interface):
    """A Binary or SourcePackage name.

    This exists to make it easier for users to find the package they want
    to report a bug in.
    """

    name = TextLine(title=_('Binary or Source package name'),
                    required=True, constraint=name_validator)

