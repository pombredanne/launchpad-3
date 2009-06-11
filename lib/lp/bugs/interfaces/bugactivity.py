# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Bug activity interfaces."""

__metaclass__ = type

__all__ = [
    'IBugActivity',
    'IBugActivitySet',
    ]

from zope.interface import Interface
from zope.schema import Datetime, Int, Text, TextLine

from canonical.launchpad import _

class IBugActivity(Interface):
    """A log of all things that have happened to a bug."""

    bug = Int(title=_('Bug ID'))
    datechanged = Datetime(title=_('Date Changed'))
    person = Int(title=_('Person'))
    whatchanged = TextLine(title=_('What Changed'))
    oldvalue = TextLine(title=_('Old Value'))
    newvalue = TextLine(title=_('New Value'))
    message = Text(title=_('Message'))


class IBugActivitySet(Interface):
    """The set of all bug activities."""

    def new(bug, datechanged, person, whatchanged,
            oldvalue=None, newvalue=None, message=None):
        """Creates a new log of what happened to a bug and returns it."""
