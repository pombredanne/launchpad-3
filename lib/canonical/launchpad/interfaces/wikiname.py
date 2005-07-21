# Copyright 2004 Canonical Ltd.  All rights reserved.

from zope.schema import Int, TextLine
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

__all__ = ['UBUNTU_WIKI_URL', 'IWikiName', 'IWikiNameSet']

#
# Wiki Interfaces
#

UBUNTU_WIKI_URL = 'http://www.ubuntulinux.com/wiki/'


class IWikiName(Interface):
    """Wiki for Users"""
    id = Int(title=_("Database ID"), required=True, readonly=True)
    person = Int(title=_("Owner"), required=True)
    wiki = TextLine(title=_("Wiki host"), required=True)
    wikiname = TextLine(title=_("Wikiname"), required=True)
    url = Attribute("The URL for this wiki home page.")


class IWikiNameSet(Interface):
    """The set of WikiNames."""

    def new(personID, wiki, wikiname):
        """Create a new WikiName pointing to the given Person."""

    def exists(wikiname, wiki=UBUNTU_WIKI_URL):
        """Does a given wikiname & wiki pair already exist?"""

