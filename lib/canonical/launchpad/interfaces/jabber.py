# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Jabber interfaces."""

__metaclass__ = type

__all__ = [
    'IJabberID',
    'IJabberIDSet',
    ]

from zope.schema import Int, Object, TextLine
from zope.interface import Interface

from canonical.lazr.rest.declarations import (
    export_as_webservice_entry, exported)

from canonical.launchpad import _


class IJabberID(Interface):
    """Jabber specific user ID """
    export_as_webservice_entry()
    id = Int(title=_("Database ID"), required=True, readonly=True)
    # schema=Interface will be overriden in person.py because of circular
    # dependencies.
    person = exported(
        Object(title=_("Owner"), required=True, schema=Interface))
    jabberid = exported(
        TextLine(title=_("Jabber user ID"), required=True))

    def destroySelf():
        """Delete this JabberID from the database."""


class IJabberIDSet(Interface):
    """The set of JabberIDs."""

    def new(person, jabberid):
        """Create a new JabberID pointing to the given Person."""

    def getByJabberID(jabberid, default=None):
        """Return the JabberID with the given jabberid.

        Return the default value if not found.
        """

    def getByPerson(person):
        """Return all JabberIDs for the given person."""

