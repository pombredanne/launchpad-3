# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Binary Package Release Contents interface."""

__metaclass__ = type

__all__ = [
    'IBinaryPackageReleaseContents',
    'IBinaryPackageReleaseContentsSet',
    ]

from lazr.restful.fields import Reference
from zope.interface import Interface

from canonical.launchpad import _
from lp.soyuz.interfaces.binarypackagepath import IBinaryPackagePath
from lp.soyuz.interfaces.binarypackagerelease import IBinaryPackageRelease


class IBinaryPackageReleaseContents(Interface):
    """A file contained by an `IBinaryPackageRelease`."""
    binarypackagerelease = Reference(
        IBinaryPackageRelease, title=_('Binary Package Release'),
        required=True, readonly=True)
    binarypackagepath = Reference(
        IBinaryPackagePath, title=_('Binary Package Pathname'),
        required=True, readonly=True)


class IBinaryPackageReleaseContentsSet(Interface):

    def add(bpr):
        """Add the contents of the given binary package release.

        :param: bpr: The `IBinaryPackageRelease` to add.

        :return: True on success, False on failure.
        """

    def remove(bpr):
        """Remove the contents of the given binary package release.

        :param: bpr: The `IBinaryPackageRelease` to remove.
        """
