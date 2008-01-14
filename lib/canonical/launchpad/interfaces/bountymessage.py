# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Bounty message interfaces."""

__metaclass__ = type

__all__ = [
    'IBountyMessage',
    ]

from zope.interface import Interface, Attribute
from canonical.launchpad import _

class IBountyMessage(Interface):
    """A link between a bounty and a message."""

    bounty = Attribute("The bounty.")
    message = Attribute("The message.")


