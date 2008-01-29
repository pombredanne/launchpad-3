# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Schema extensions for HTTP resources."""

__metaclass__ = type
__all__ = [
    'CollectionField',
]

from zope.interface import implements
from zope.schema._field import AbstractCollection

from canonical.lazr.interfaces.rest import ICollectionField

class CollectionField(AbstractCollection):
    """A collection associated with an entry."""
    implements(ICollectionField)
