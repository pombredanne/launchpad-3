# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""NameBlacklist interfaces."""

__metaclass__ = type

__all__ = [
    'INameBlacklist',
    'INameBlacklistSet',
    ]

from zope.interface import Interface
from zope.schema import (
    Int,
    Text,
    TextLine,
    )

from canonical.launchpad import _


class INameBlacklist(Interface):
    """The interface for the NameBlacklist table."""

    id = Int(title=_('ID'), required=True, readonly=True)
    regexp = TextLine(title=_('Regular expression'), required=True)
    comment = Text(title=_('Comment'), required=False)


class INameBlacklistSet(Interface):
    """The set of INameBlacklist objects."""

    def getAll():
        """Return all the name blacklist expressions."""

    def create(regexp, comment=None):
        """Create and return a new NameBlacklist with given arguments."""

    def get(id):
        """Return the NameBlacklist with the given id or None."""

    def getByRegExp(regexp):
        """Return the NameBlacklist with the given regexp or None."""
