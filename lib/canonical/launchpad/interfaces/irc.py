# Copyright 2004 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""IRC interfaces."""

__metaclass__ = type

__all__ = [
    'IIrcID',
    'IIrcIDSet',
    ]

from zope.schema import Int, TextLine
from zope.interface import Interface
from canonical.launchpad import _

from canonical.lazr.rest.declarations import export_as_webservice_entry


class IIrcID(Interface):
    """Wiki for Users"""
    export_as_webservice_entry()
    id = Int(title=_("Database ID"), required=True, readonly=True)
    person = Int(title=_("Owner"), required=True, readonly=True)
    network = TextLine(title=_("IRC network"), required=True)
    nickname = TextLine(title=_("Nickname"), required=True)

    def destroySelf():
        """Delete this IrcId from the database."""


class IIrcIDSet(Interface):
    """The set of IrcIDs."""

    def new(person, network, nickname):
        """Create a new IrcID pointing to the given Person."""

    def get(id):
        """Return the `IIrcID` with the given id or None."""
