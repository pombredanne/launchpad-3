# Copyright 2004 Canonical Ltd.  All rights reserved.

from zope.schema import Int, TextLine
from zope.interface import Interface
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

#
# Jabber Interfaces
#

class IJabberID(Interface):
    """Jabber specific user ID """
    id = Int(title=_("Database ID"), required=True, readonly=True)
    person = Int(title=_("Owner"), required=True)
    jabberid = TextLine(title=_("Jabber user ID"), required=True)

