# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Jabber interfaces."""

__metaclass__ = type

__all__ = [
    'IJabberID',
    'IJabberIDSet',
    ]

from zope.schema import Int, TextLine
from zope.interface import Interface

from canonical.lazr.rest.declarations import (
    export_as_webservice_entry, exported)
from canonical.lazr.rest.schema import Reference

from canonical.launchpad import _
from canonical.launchpad.interfaces.launchpad import IHasOwner


class IJabberID(IHasOwner):
    """Jabber specific user ID """
    export_as_webservice_entry()
    id = Int(title=_("Database ID"), required=True, readonly=True)
    # schema=Interface will be overriden in person.py because of circular
    # dependencies.
    person = exported(
        Reference(
            title=_("Owner"), required=True, schema=Interface, readonly=True))
    jabberid = exported(
        TextLine(title=_("Jabber user ID"), required=True))

    def destroySelf():
        """Delete this JabberID from the database."""


class IJabberIDSet(Interface):
    """The set of JabberIDs."""

    def new(person, jabberid):
        """Create a new JabberID pointing to the given Person."""

    def getByJabberID(jabberid):
        """Return the JabberID with the given jabberid or None."""

    def getByPerson(person):
        """Return all JabberIDs for the given person."""

