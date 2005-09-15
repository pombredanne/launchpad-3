# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Manifest entry interfaces."""

__metaclass__ = type

__all__ = [
    'IManifestEntry',
    ]

from zope.interface import Interface, Attribute

class IManifestEntry(Interface):
    """A manifest entry."""
    branch = Attribute("A branch")


