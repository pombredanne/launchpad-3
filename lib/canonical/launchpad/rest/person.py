# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad people."""

__metaclass__ = type
__all__ = [
    'PersonCollectionResource',
    ]


from canonical.lazr.rest import (CollectionResource, EntryResource)


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

    def find(self):
        return [PersonResource(p) for p in
                getUtility(IPersonSet).getAllValidPersons()]
