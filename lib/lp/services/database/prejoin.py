# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Prejoin for Storm."""

__metaclass__ = type
__all__ = ['prejoin']

from lazr.delegates import delegates
from storm.zope.interfaces import IResultSet


class PrejoinResultSet:
    """Prejoin support.

    Wrap a ResultSet, trimming unwanted items. The unwanted items
    are still pulled from the database and populate the Storm caches.

    This is a temporary solution, as as count() performs an unnecessary
    join making it slower and __contains__() is not implemented at all.
    The preferred solution is support in Storm core, so we can just do
    something like:

    # Select Product, but prejoin the owner as well.
    >>> join = store.find((Product, Person), Product.name == name)
    >>> results = prejoin(join, slice(0, 1))
    """
    delegates(IResultSet, context='result_set')

    def __init__(self, result_set, return_slice=slice(0, 1)):
        self.result_set = result_set
        self.return_slice = return_slice

    def _chain(self, result_set):
        return PrejoinResultSet(result_set, self.return_slice)

    def _chomp(self, row):
        if row is None:
            return None
        elems = row[self.return_slice]
        if len(elems) == 1:
            return elems[0]
        else:
            return elems

    def copy(self):
        """See `IResultSet`."""
        return self._chain(self.result_set.copy())

    def config(self, distinct=None, offset=None, limit=None):
        """See `IResultSet`."""
        self.result_set.config(distinct, offset, limit)
        return self

    def order_by(self, *args):
        """See `IResultSet`."""
        return self._chain(self.result_set.order_by(*args))

    def difference(self, *args, **kw):
        """See `IResultSet`."""
        raise NotImplementedError("difference")

    def group_by(self, *args, **kw):
        """See `IResultSet`."""
        raise NotImplementedError("group_by")

    def having(self, *args, **kw):
        """See `IResultSet`."""
        raise NotImplementedError("having")

    def intersection(self, *args, **kw):
        """See `IResultSet`."""
        raise NotImplementedError("intersection")

    def union(self, *args, **kw):
        """See `IResultSet`."""
        raise NotImplementedError("union")

    def __iter__(self):
        """See `IResultSet`."""
        return (self._chomp(row) for row in self.result_set)

    def __getitem__(self, index):
        """See `IResultSet`."""
        if isinstance(index, slice):
            return self._chain(self.result_set[index])
        else:
            return self._chomp(self.result_set[index])

    def __contains__(self, item):
        """See `IResultSet`."""
        raise NotImplementedError("__contains__")

    def any(self):
        """See `IResultSet`."""
        return self._chomp(self.result_set.any())

    def first(self):
        """See `IResultSet`."""
        return self._chomp(self.result_set.first())

    def last(self):
        """See `IResultSet`."""
        return self._chomp(self.result_set.last())

    def one(self):
        """See `IResultSet`."""
        return self._chomp(self.result_set.one())

    def cached(self):
        """See `IResultSet`."""
        raise NotImplementedError("cached")

prejoin = PrejoinResultSet
