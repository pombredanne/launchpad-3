# Copyright 2004 Canonical Ltd.  All rights reserved.

from zope.schema import Int, TextLine
from zope.interface import Interface
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


#
# Wiki Interfaces
#

class IWikiName(Interface):
    """Wiki for Users"""
    id = Int(title=_("Database ID"), required=True, readonly=True)
    person = Int(title=_("Owner"), required=True)
    wiki = TextLine(title=_("Wiki host"), required=True)
    wikiname = TextLine(title=_("Wikiname"), required=True)


class IWikiNameSet(Interface):
    """The set of WikiNames."""

    def new(personID, wiki, wikiname):
        """Create a new WikiName pointing to the given Person."""

