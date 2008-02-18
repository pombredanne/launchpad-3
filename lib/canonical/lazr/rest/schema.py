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
    # We subclass AbstractCollection instead of List because List
    # has a _type of list, and we don't want to have to implement list
    # semantics for this class.
    implements(ICollectionField)

    def __init__(self, *args, **kwargs):
        self.is_entry_container = kwargs.setdefault(
            'is_entry_container', False)
        del(kwargs['is_entry_container'])
        super(CollectionField, self).__init__(*args, **kwargs)
