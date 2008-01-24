# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Schema extensions for HTTP resources."""

__metaclass__ = type
__all__ = [
    'CollectionField',
]

from zope.interface import implements
from zope.schema import Object

from canonical.lazr.interfaces.rest import ICollectionField

class CollectionField(Object):
    __doc__ == ICollectionField.__doc__
    implements(ICollectionField)
