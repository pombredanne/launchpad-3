# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Source package format interfaces."""

__metaclass__ = type

__all__ = [
    'SourcePackageFormat',
    'ISourcePackageFormatSelection',
    'ISourcePackageFormatSelectionSet',
    ]

from zope.interface import Attribute, Interface
from lazr.enum import DBEnumeratedType, DBItem


class SourcePackageFormat(DBEnumeratedType):
    """Source package format

    There are currently three formats of Debian source packages. The Format
    field in the .dsc file must specify one of these formats.
    """

    FORMAT_1_0 = DBItem(0, """
        1.0

        Specifies either a native (having a single tar.gz) or non-native
        (having an orig.tar.gz and a diff.gz) package. Supports only gzip
        compression.
        """)

    FORMAT_3_0_QUILT = DBItem(1, """
        3.0 (quilt)

        Specifies a non-native package, with an orig.tar.* and a debian.tar.*.
        Supports gzip and bzip2 compression.
        """)

    FORMAT_3_0_NATIVE = DBItem(2, """
        3.0 (native)

        Specifies a native package, with a single tar.*. Supports gzip and
        bzip2 compression.
        """)


class ISourcePackageFormatSelection(Interface):
    """A source package format allowed within a DistroSeries."""

    id = Attribute("ID")
    distroseries = Attribute("Target series")
    format = Attribute("Permitted source package format")


class ISourcePackageFormatSelectionSet(Interface):
    """Set manipulation tools for the SourcePackageFormatSelection table."""

    def getBySeriesAndFormat(distroseries, format):
        """Return the ISourcePackageFormatSelection for the given series and
        format."""

    def add(distroseries, format):
        """Allow the given source package format in the given series."""
