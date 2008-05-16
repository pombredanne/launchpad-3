# Copyright 2004 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""IRC interfaces."""

__metaclass__ = type

__all__ = [
    'IIrcID',
    'IIrcIDSet',
    ]

from zope.schema import Int, Object, TextLine
from zope.interface import Interface

from canonical.lazr.rest.declarations import (
    export_as_webservice_entry, exported)

from canonical.launchpad import _


class IIrcID(Interface):
    """Wiki for Users"""
    export_as_webservice_entry()
    id = Int(title=_("Database ID"), required=True, readonly=True)
    # schema=Interface will be overriden in person.py because of circular
    # dependencies.
    person = exported(
        Object(title=_("Owner"), required=True, schema=Interface))
    network = exported(
        TextLine(title=_("IRC network"), required=True))
    nickname = exported(
        TextLine(title=_("Nickname"), required=True))

    def destroySelf():
        """Delete this IrcId from the database."""


class IIrcIDSet(Interface):
    """The set of IrcIDs."""

    def new(person, network, nickname):
        """Create a new IrcID pointing to the given Person."""

    def get(id):
        """Return the `IIrcID` with the given id or None."""
