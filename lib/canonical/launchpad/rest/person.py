# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad people."""

__metaclass__ = type
__all__ = [
    'PersonResource',
    'PersonCollectionResource',
    ]


from zope.component import (adapts, getUtility)
from zope.interface import implements
from canonical.lp import decorates
from canonical.lazr.rest import (CollectionResource, EntryResource)
from canonical.launchpad.interfaces import (
    IPerson, IPersonResource, IPersonSet)


class PersonResource(EntryResource):
    """A person."""
    implements(IPersonResource)
    decorates(IPersonResource, context="person")
    adapts(IPerson)

    def __init__(self, person):
        """Associate this resource with a specific person."""
        self.person = person

    def resourceInterface(self):
        return IPersonResource

    @property
    def name(self):
        return self.person.name


class PersonCollectionResource(CollectionResource):
    """A collection of people."""

    def lookupEntry(self, request, name):
        """Find a person by name."""
        person = getUtility(IPersonSet).getByName(name)
        if person is None:
            return None
        else:
            return PersonResource(person)

    def find(self):
        return [PersonResource(p) for p in
                getUtility(IPersonSet).getAllValidPersons()]
