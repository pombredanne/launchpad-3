# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Binary Package Path interface."""

__metaclass__ = type

__all__ = [
    'IBinaryPackagePath',
    'IBinaryPackagePathSource',
    ]

from zope.interface import Interface
from zope.schema import (
    Int,
    TextLine,
    )

from canonical.launchpad import _


class IBinaryPackagePath(Interface):
    """The path of a file contained in a binary package.

    A binary package release is a representation of a binary package in
    one or more releases. This class models the files contained within
    the binary package.
    """
    id = Int(title=_('ID'), required=True, readonly=True)
    path = TextLine(title=_('Full path name'), required=True, readonly=True)


class IBinaryPackagePathSource(Interface):

    def getOrCreate(path):
        """Fetch the ID of the given path name, or create it.

        :param: path: The full path name to query or create.

        :return: An ID.
        """
