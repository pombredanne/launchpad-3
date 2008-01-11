# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad people."""

__metaclass__ = type
__all__ = [
    'PersonResource',
    'PersonCollectionResource',
    ]


from zope.component import adapts, getAdapter, getUtility
from zope.interface import implements
from canonical.lp import decorates
from canonical.lazr.rest import CollectionResource, EntryResource
from canonical.launchpad.interfaces import (
    IPerson, IPersonResourceSchema, IPersonSet)


class PersonResource(EntryResource):
    """A person."""
    decorates(IPersonResourceSchema, context="context")
    adapts(IPerson)
    schema = IPersonResourceSchema

    def __init__(self, context):
        """Associate this resource with a specific person."""
        self.context = context


class PersonCollectionResource(CollectionResource):
    """A collection of people."""

    def find(self):
        return [getAdapter(p, IPersonResourceSchema) for p in
                getUtility(IPersonSet).getAllValidPersons()]
