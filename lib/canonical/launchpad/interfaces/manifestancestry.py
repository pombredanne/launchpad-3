# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Manifest Ancestry interfaces."""

__metaclass__ = type

__all__ = [
    'IManifestAncestry',
    ]

from zope.schema import Int, Choice
from zope.interface import Interface
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class IManifestAncestry(Interface):
    """A Manifest Ancestry record.

    It relates one Manifest with another,
    providing a link from a manifest to the one it is based on and those
    which were merged in to product it.
    """

    id = Int(title=_("Manifest Ancestry ID"))

    parent = Choice(title=_("Parent Manifest"), required=True,
                    vocabulary="Manifest")
    child = Choice(title=_("Child Manifest"), required=True,
                   vocabulary="Manifest")
