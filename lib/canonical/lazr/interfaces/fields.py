# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Interfaces for LAZR zope.schema fields."""

__metaclass__ = type
__all__ = [
    'ICollectionField',
    ]

from zope.schema.interfaces import ISequence


class ICollectionField(ISequence):
    """A field representing a sequence.

    All iterables satisfy this collection field.
    """

