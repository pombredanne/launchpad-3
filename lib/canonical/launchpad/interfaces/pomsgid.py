# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute

__metaclass__ = type

__all__ = ('IPOMsgID', )

class IPOMsgID(Interface):
    """A PO message ID."""

    msgid = Attribute("A msgid string.")
