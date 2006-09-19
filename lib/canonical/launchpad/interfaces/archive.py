# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Archive interfaces."""

__metaclass__ = type

__all__ = [
    'IArchive',
    ]

from zope.interface import Interface, Attribute

from canonical.launchpad import _


class IArchive(Interface):
    """An Archive interface"""
    id = Attribute("The archive ID.")
