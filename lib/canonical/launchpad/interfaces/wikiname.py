# Copyright 2004 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

__all__ = [
    'UBUNTU_WIKI_URL',
    'IWikiName',
    'IWikiNameSet',
    ]

from zope.schema import Int, TextLine
from zope.interface import Interface, Attribute
from canonical.launchpad import _

from canonical.lazr.rest.declarations import export_as_webservice_entry


UBUNTU_WIKI_URL = 'https://wiki.ubuntu.com/'


class IWikiName(Interface):
    """Wiki for Users"""
    export_as_webservice_entry()
    id = Int(title=_("Database ID"), required=True, readonly=True)
    person = Int(title=_("Owner"), required=True)
    wiki = TextLine(title=_("Wiki host"), required=True)
    wikiname = TextLine(title=_("Wikiname"), required=True)
    url = Attribute("The URL for this wiki home page.")

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

    def get(id):
        """Return the WikiName with the given id or None."""

    def new(person, wiki, wikiname):
        """Create a new WikiName pointing to the given Person."""

    def exists(wikiname, wiki=UBUNTU_WIKI_URL):
        """Does a given wikiname & wiki pair already exist?"""
