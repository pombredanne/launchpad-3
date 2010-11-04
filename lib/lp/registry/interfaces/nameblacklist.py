# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""NameBlackList interfaces."""

__metaclass__ = type

__all__ = [
    'INameBlackList',
    'INameBlackListSet',
    ]

from zope.interface import Interface
from zope.schema import (
    Int,
    Text,
    TextLine,
    )

from canonical.launchpad import _


class INameBlackList(Interface):
    """The interface for the NameBlackList table."""

    id = Int(title=_('ID'), required=True, readonly=True)
    regexp = TextLine(title=_('Regular expression'), required=True)
    comment = Text(title=_('Comment'), required=False)


class INameBlackListSet(Interface):
    """The set of INameBlackList objects."""

    def create(regexp, comment=None):
        """Create and return a new NameBlackList with given arguments."""

    def get(id):
        """Return the NameBlackList with the given id or None."""
