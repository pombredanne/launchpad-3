# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad people."""

__metaclass__ = type
__all__ = [
    'PersonResource',
    'PersonCollectionResource',
    ]


from zope.component import adapts, getAdapter, getUtility
from zope.interface import implements
from canonical.lazr.interfaces import ICollectionResource
from canonical.lazr.rest import EntryResourceController
from canonical.launchpad.interfaces import (
    IPerson, IPersonResource, IPersonSet)
from canonical.lp import decorates


class PersonResource:
    """A person."""
    adapts(IPerson)
    decorates(IPersonResource)
    schema = IPersonResource

    def __init__(self, context):
        self.context = context


class PersonCollectionResource:
    """A collection of people."""
    implements(ICollectionResource)

    def find(self):
        return [EntryResourceController(p) for p in
                getUtility(IPersonSet).getAllValidPersons()]
