# Copyright 2004 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

__all__ = [
    'IWikiName',
    'IWikiNameSet',
    ]

from zope.schema import Int, TextLine
from zope.interface import Interface

from lazr.restful.fields import Reference
from lazr.restful.declarations import (
    export_as_webservice_entry, exported)

from canonical.launchpad import _
from canonical.launchpad.fields import URIField
from canonical.launchpad.interfaces.launchpad import IHasOwner


class IWikiName(IHasOwner):
    """Wiki for Users"""
    export_as_webservice_entry()
    id = Int(title=_("Database ID"), required=True, readonly=True)
    # schema=Interface will be overriden in person.py because of circular
    # dependencies.
    person = exported(
        Reference(
            title=_("Owner"), schema=Interface, required=True, readonly=True))
    wiki = exported(
        URIField(title=_("Wiki host"),
                 allowed_schemes=['http', 'https'],
                 required=True))
    wikiname = exported(
        TextLine(title=_("Wikiname"), required=True))
    url = exported(
        TextLine(title=_("The URL for this wiki home page."), readonly=True))

    def destroySelf():
        """Remove this WikiName from the database."""


class IWikiNameSet(Interface):
    """The set of WikiNames."""

    def getByWikiAndName(wiki, wikiname):
        """Return the WikiName with the given wiki and wikiname.

        Return None if it doesn't exists.
        """

    def get(id):
        """Return the WikiName with the given id or None."""

    def new(person, wiki, wikiname):
        """Create a new WikiName pointing to the given Person."""
