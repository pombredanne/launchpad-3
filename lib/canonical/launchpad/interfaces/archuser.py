# Copyright 2004 Canonical Ltd.  All rights reserved.

from zope.schema import Int, TextLine
from zope.interface import Interface
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


#
# Arch users Interfaces
#

class IArchUserID(Interface):
    """ARCH specific user ID """
    id = Int(title=_("Database ID"), required=True, readonly=True)
    person = Int(title=_("Owner"), required=True, readonly=True)
    archuserid = TextLine(title=_("ARCH user ID"), required=True)

