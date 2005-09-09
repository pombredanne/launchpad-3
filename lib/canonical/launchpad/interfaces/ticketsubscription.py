# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Ticket subscription interfaces."""

__metaclass__ = type

__all__ = [
    'ITicketSubscription',
    ]

from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class ITicketSubscription(Interface):
    """A subscription for a person to a ticket."""

    person = Attribute("The subscriber.")
    ticket = Attribute("The ticket.")

