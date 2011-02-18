# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213,W0611
"""Interfaces that define common roles associated with objects."""

__metaclass__ = type

__all__ = [
    'IHasOwner',
    ]


from zope.interface import (
    Attribute,
    Interface,
    )


class IHasOwner(Interface):
    """An object that has an owner."""

    owner = Attribute("The object's owner, which is an IPerson.")
