# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Bug activity interfaces."""

__metaclass__ = type

__all__ = [
    'IBugActivity',
    ]

from zope.i18nmessageid import MessageIDFactory
from zope.interface import Interface
from zope.schema import Datetime, Int, Text, TextLine

_ = MessageIDFactory('launchpad')

class IBugActivity(Interface):
    """A log of all things that have happened to a bug."""

    bug = Int(title=_('Bug ID'))
    datechanged = Datetime(title=_('Date Changed'))
    person = Int(title=_('Person'))
    whatchanged = TextLine(title=_('What Changed'))
    oldvalue = TextLine(title=_('Old Value'))
    newvalue = TextLine(title=_('New Value'))
    message = Text(title=_('Message'))

