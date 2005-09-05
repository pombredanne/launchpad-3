# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Package file interfaces."""

__metaclass__ = type

__all__ = [
    'IBinaryPackageFile',
    'ISourcePackageReleaseFile',
    ]

from zope.schema import Int
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

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
    url = Attribute("IDownloadURL instance")

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

    url = Attribute("IDownloadURL instance")
