# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213,W0611
"""Interfaces that define common roles associated with objects."""

__metaclass__ = type

__all__ = [
    'IHasOwner',
    ]


from zope.interface import Interface, Attribute

from canonical.launchpad import _


class IHasOwner(Interface):
    """An object that has an owner."""

    owner = Attribute("The object's owner, which is an IPerson.")
