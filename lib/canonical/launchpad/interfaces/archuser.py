# Copyright 2004 Canonical Ltd.  All rights reserved.

"""Interfaces related to users of Arch."""

__metaclass__ = type

__all__ = [
    'IArchUserID',
    'IArchUserIDSet',
    ]

from zope.schema import Int, TextLine
from zope.interface import Interface
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')


class IArchUserID(Interface):
    """ARCH specific user ID """
    id = Int(title=_("Database ID"), required=True, readonly=True)
    person = Int(title=_("Owner"), required=True, readonly=True)
    archuserid = TextLine(title=_("ARCH user ID"), required=True)

    def destroySelf():
        """Delete this ArchUserID from the database."""


class IArchUserIDSet(Interface):
    """The set of ArchUserIDs."""

    def new(personID, archuserid):
        """Create a new ArchUserID pointing to the given Person."""

