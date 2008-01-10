# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad people."""

__metaclass__ = type
__all__ = [
    'PersonResource',
    'PersonCollectionResource',
    ]


from zope.component import adapts, getUtility
from zope.interface import implements
from canonical.lp import decorates
from canonical.lazr.rest import CollectionResource, EntryResource
from canonical.launchpad.interfaces import (
    IPerson, IPersonResource, IPersonSet)


class PersonResource(EntryResource):
    """A person."""
    decorates(IPersonResource, context="context")
    adapts(IPerson)

    schema = IPersonResource

    def __init__(self, context):
        """Associate this resource with a specific person."""
        self.context = context


class PersonCollectionResource(CollectionResource):
    """A collection of people."""

    def find(self):
        return [PersonResource(p) for p in
                getUtility(IPersonSet).getAllValidPersons()]
