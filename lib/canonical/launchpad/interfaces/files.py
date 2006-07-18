# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Package file interfaces."""

__metaclass__ = type

__all__ = [
    'IDownloadURL',
    'ISoyuzFile',
    'IBinaryPackageFile',
    'ISourcePackageReleaseFile',
    ]

from zope.schema import Int
from zope.interface import Interface, Attribute
from canonical.launchpad import _

class IDownloadURL(Interface):
    filename = Attribute("Downloadable Package name")
    fileurl = Attribute("Package full url")


class ISoyuzFile(Interface):
    """Provide the implementation of 'url' property.

    Return an IDownloadURL instance.
    """
    url = Attribute("IDownloadURL instance or None if Librarian isn't "
                    "running or the file was not found.")

class IBinaryPackageFile(Interface):
    """A binary package to librarian link record."""

    id = Int(
            title=_('ID'), required=True, readonly=True,
            )
    binarypackage = Int(
            title=_('The binary package being published'), required=True,
            readonly=False,
            )

    libraryfile = Int(
            title=_('The library file alias for this .deb'), required=True,
            readonly=False,
            )

    filetype = Int(
            title=_('The type of this file'), required=True, readonly=False,
            )



class ISourcePackageReleaseFile(Interface):
    """A source package release to librarian link record."""

    id = Int(
            title=_('ID'), required=True, readonly=True,
            )
    sourcepackagerelease = Int(
            title=_('The sourcepackagerelease being published'), required=True,
            readonly=False,
            )

    libraryfile = Int(
            title=_('The library file alias for this file'), required=True,
            readonly=False,
            )

    filetype = Int(
            title=_('The type of this file'), required=True, readonly=False,
            )
