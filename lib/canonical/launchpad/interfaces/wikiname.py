# Copyright 2004 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

__all__ = [
    'UBUNTU_WIKI_URL',
    'IWikiName',
    'IWikiNameSet',
    ]

from zope.schema import Int, Object, TextLine
from zope.interface import Interface

from canonical.lazr.rest.declarations import (
    export_as_webservice_entry, exported)

from canonical.launchpad import _


UBUNTU_WIKI_URL = 'https://wiki.ubuntu.com/'


class IWikiName(Interface):
    """Wiki for Users"""
    export_as_webservice_entry()
    id = Int(title=_("Database ID"), required=True, readonly=True)
    # schema=Interface will be overriden in person.py because of circular
    # dependencies.
    person = exported(
        Object(title=_("Owner"), schema=Interface, required=True))
    wiki = exported(
        TextLine(title=_("Wiki host"), required=True))
    wikiname = exported(
        TextLine(title=_("Wikiname"), required=True))
    url = exported(
        TextLine(title=_("The URL for this wiki home page.")))

    def destroySelf():
        """Remove this WikiName from the database."""


class IWikiNameSet(Interface):
    """The set of WikiNames."""

    def getByWikiAndName(wiki, wikiname):
        """Return the WikiName with the given wiki and wikiname.

        Return None if it doesn't exists.
        """

    def getUbuntuWikiByPerson(person):
        """Return the Ubuntu WikiName for the given person."""

    def getOtherWikisByPerson(person):
        """Return all WikiNames of the given person that are not the Ubuntu
        one."""

    def getAllWikisByPerson(person):
        """Return all WikiNames of the given person."""

    def get(id, default=None):
        """Return the WikiName with the given id.

        Return the default value if nof found.
        """

    def new(person, wiki, wikiname):
        """Create a new WikiName pointing to the given Person."""

    def exists(wikiname, wiki=UBUNTU_WIKI_URL):
        """Does a given wikiname & wiki pair already exist?"""

