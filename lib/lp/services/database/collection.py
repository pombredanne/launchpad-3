# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A generic collection of database objects."""

__metaclass__ = type
__all__ = [
    'Collection',
    ]

from zope.component import getUtility

from storm.expr import LeftJoin
from storm.store import FindSpec

from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR, IStoreSelector, MAIN_STORE)


class Collection(object):
    """An arbitrary collection of database objects."""

    store = None
    using = None

    def __init__(self, base, *conditions):
        """Construct a collection, possibly based on another one."""
        if base is None:
            base_conditions = (True, )
            self.using = tuple()
        else:
            base_conditions = base.conditions
            self.using = base.using
        self.conditions = base_conditions + conditions
        
    def use(self, store):
        """Return a copy of this collection that uses the given store."""
        new_collection = Collection(self)
        new_collection.store = store
        return new_collection

    def outer_join(self, cls, *conditions):
        """Outer-join `cls` into the query."""
        join = LeftJoin(cls, *conditions)
        new_collection = Collection(self)
        new_collection.using = self.using + (join, )
        return new_collection
    
    def select(self, *values):
        """Return the selected values from the collection."""
        if self.store is None:
            store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        else:
            store = self.store
            
        if len(self.using) == 0:
            source = store
        else:
            find_spec = FindSpec(*values)
            columns, tables = find_spec.get_columns_and_tables()
            source = store.using(self.using + tables)
            
        if len(values) > 1:
            return source.find(values, *self.conditions)
        else:
            return source.find(*(values + self.conditions))
