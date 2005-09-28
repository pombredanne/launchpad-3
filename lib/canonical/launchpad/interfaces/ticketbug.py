# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Interfaces for linking between a Ticket and a Bug."""

__metaclass__ = type

__all__ = [
    'ITicketBug',
    ]

from zope.interface import Interface
from zope.schema import Int, Choice
from zope.i18nmessageid import MessageIDFactory

from canonical.launchpad.interfaces import valid_bug_number

_ = MessageIDFactory('launchpad')

class ITicketBug(Interface):
    """A link between a Bug and a ticket."""

    ticket = Int(title=_('Ticket Number'), required=True,
        readonly=True)
    bug = Int(title=_('Bug Number'), required=True, readonly=True,
        description=_("The number of the Malone bug report."),
        constraint=valid_bug_number)
