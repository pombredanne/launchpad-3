# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Binary Package Path interface."""

__metaclass__ = type

__all__ = [
    'IBinaryPackagePath',
    'IBinaryPackagePathSet',
    ]

from zope.interface import Interface
from zope.schema import (
    Int,
    TextLine,
    )

from canonical.launchpad import _


class IBinaryPackagePath(Interface):
    """The path of a file contained in a binary package."""
    id = Int(title=_('ID'), required=True, readonly=True)
    path = TextLine(title=_('Full path name'), required=True, readonly=True)


class IBinaryPackagePathSet(Interface):

    def getOrCreate(path):
        """Fetch the ID of the given path name, or create it.

        :param: path: The full path name to query or create.

        :return: A `IBinaryPackagePath`.
        """
