# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Package file interfaces."""

__metaclass__ = type

__all__ = [
    'IBinaryPackageFile',
    'IBinaryPackageFileSet',
    'ISourcePackageReleaseFile',
    'ISourcePackageReleaseFileSet',
    ]

from zope.interface import Interface
from zope.schema import (
    Bool,
    Int,
    )

from canonical.launchpad import _


class IBinaryPackageFile(Interface):
    """A binary package to librarian link record."""

    id = Int(
            title=_('ID'), required=True, readonly=True,
            )
    binarypackagerelease = Int(
            title=_('The binarypackagerelease being published'),
            required=True, readonly=False,
            )

    libraryfile = Int(
            title=_('The library file alias for this .deb'), required=True,
            readonly=False,
            )

    filetype = Int(
            title=_('The type of this file'), required=True, readonly=False,
            )


class IBinaryPackageFileSet(Interface):
    """The set of all `BinaryPackageFile`s."""

    def getByPackageUploadIDs(package_upload_ids):
        """Return `BinaryPackageFile`s for the `PackageUpload` IDs."""


class ISourcePackageReleaseFile(Interface):
    """A source package release to librarian link record."""

    id = Int(
            title=_('ID'), required=True, readonly=True,
            )
    sourcepackagerelease = Int(
            title=_('The sourcepackagerelease being published'),
            required=True,
            readonly=False,
            )

    libraryfile = Int(
            title=_('The library file alias for this file'), required=True,
            readonly=False,
            )

    filetype = Int(
            title=_('The type of this file'), required=True, readonly=False,
            )

    is_orig = Bool(
            title=_('Whether this file is an original tarball'),
            required=True, readonly=False,
            )


class ISourcePackageReleaseFileSet(Interface):
    """The set of all `SourcePackageRelease`s."""

    def getByPackageUploadIDs(package_upload_ids):
        """Return `SourcePackageReleaseFile`s for the `PackageUpload` IDs."""
