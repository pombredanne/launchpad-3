# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad people."""

__metaclass__ = type
__all__ = [
    'PersonResource',
    'PersonCollectionResource',
    ]


from zope.component import adapts, getAdapter, getUtility
from zope.interface import implements
from canonical.lazr.interfaces import (
    ICollectionResource, IEntryResourceController)
from canonical.launchpad.interfaces import (
    IPerson, IPersonResource, IPersonSet)


class PersonResource:
    """A person."""
    adapts(IPerson)
    schema = IPersonResource


class PersonCollectionResource:
    """A collection of people."""
    implements(ICollectionResource)

    def find(self):
        return [getAdapter(p, IEntryResourceController) for p in
                getUtility(IPersonSet).getAllValidPersons()]
