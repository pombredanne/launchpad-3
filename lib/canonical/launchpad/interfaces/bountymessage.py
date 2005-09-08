# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Bounty message interfaces."""

__metaclass__ = type

__all__ = [
    'IBountyMessage',
    ]

from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class IBountyMessage(Interface):
    """A link between a bounty and a message."""

    bounty = Attribute("The bounty.")
    message = Attribute("The message.")


