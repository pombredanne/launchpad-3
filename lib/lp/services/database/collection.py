# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A generic collection of database objects."""

__metaclass__ = type
__all__ = [
    'Collection',
    ]

from zope.component import getUtility

from storm.expr import LeftJoin

from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR, IStoreSelector, MAIN_STORE)


class Collection(object):
    """An arbitrary collection of database objects.

    Works as a Storm wrapper: create a collection based on another
    collection, adding joins and select conditions to taste.

    Since deserializing long strings can be very slow and isn't always
    needed by the caller, you can select any mix of classes and
    individual columns or other Storm expressions.
    """
    def __init__(self, base, *conditions, **kwargs):
        """Construct a collection, possibly based on another one.

        :param base: The collection that this collection is based on.
            The new collection will inherit its configuration.
        :param conditions: Optional Storm select conditions, e.g.
            `MyClass.attribute > 2`.
        :param classes: A class, or tuple or list of classes, that
            should go into the "FROM" clause of the new collection.
            This need not include classes that are already in the
            base collection, or that are included as outer joins.
        :param store: Optional: Storm `Store` to use.
        """
        if base is None:
            base_conditions = (True, )
            base_tables = []
        else:
            self.store = base.store
            base_conditions = base.conditions
            base_tables = list(base.tables)


        self.store = kwargs.get('store')
        if self.store is None:
            self.store = getUtility(IStoreSelector).get(
                MAIN_STORE, DEFAULT_FLAVOR)

        self.tables = (
            base_tables + self._parseTablesArg(kwargs.get('tables', [])))
        self.conditions = base_conditions + conditions

    def _parseTablesArg(self, tables):
        """Turn tables argument into a list.

        :param tables: A class, or tuple of classes, or list of classes.
        :param return: All classes that were passed in, as a list.
        """
        if isinstance(tables, tuple):
            return list(tables)
        elif isinstance(tables, list):
            return tables
        else:
            return [tables]

    def use(self, store):
        """Return a copy of this collection that uses the given store."""
        return Collection(self, store=store)

    def joinOuter(self, cls, *conditions):
        """Outer-join `cls` into the query."""
        join = LeftJoin(cls, *conditions)
        tables = [join]
        return Collection(self, tables=tables)

    def select(self, *values):
        """Return a result set containing the requested `values`."""
        if len(self.tables) == 0:
            source = self.store
        else:
            source = self.store.using(*self.tables)

        if len(values) == 1:
            values = values[0]

        return source.find(values, *self.conditions)
