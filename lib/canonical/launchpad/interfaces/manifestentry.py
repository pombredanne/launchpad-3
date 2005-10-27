# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Manifest entry interfaces."""

__metaclass__ = type

__all__ = [
    'IManifestEntry',
    ]

from zope.interface import Interface, Attribute

class IManifestEntry(Interface):
    """A manifest entry."""
    manifest = Attribute("The Manifest this entry is part of")
    sequence = Attribute("Sequence number of this entry within the manifest")

    entrytype = Attribute("Type of the entry")
    path = Attribute("Path within source package this entry produces")
    hint = Attribute("Hint as to purpose of this entry")
    parent = Attribute("Sequence number of our parent entry")

    dirname = Attribute("Directory name in the file produced by the entry")
    branch = Attribute("Branch to obtain entry content from")
    changeset = Attribute("Specific changeset on branch to get")
