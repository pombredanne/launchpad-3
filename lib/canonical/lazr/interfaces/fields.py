# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Interfaces for LAZR zope.schema fields."""

__metaclass__ = type
__all__ = [
    'ICollectionField',
    'IReference',
    ]

from zope.schema.interfaces import IObject, ISequence


class ICollectionField(ISequence):
    """A field representing a sequence.

    All iterables satisfy this collection field.
    """

class IReference(IObject):
    """A reference to an object providing a particular schema.

    Validation only enforce that the object provides the interface, not
    that all its attributes matches the schema constraints.
    """
