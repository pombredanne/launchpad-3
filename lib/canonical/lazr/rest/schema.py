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
        """Define a container object that's related to some other object.

        This will show up in the web service as a scoped collection.

        :param is_entry_container: By default, scoped collections
        contain references to entries whose self_link URLs are handled
        by the data type's parent_collection_path. Set this to True if
        the self_link URL of an entry should be handled by the scoped
        collection.
        """

        self.is_entry_container = kwargs.pop('is_entry_container', False)
        super(CollectionField, self).__init__(*args, **kwargs)
