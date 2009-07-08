# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Implementation for the IRevisionCache and IRevisionCollection."""

__metaclass__ = type
__all__ = [
    'GenericRevisionCollection',
    ]

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from lp.code.interfaces.revisioncache import IRevisionCollection
from lp.code.model.revision import Revision, RevisionCache


class GenericRevisionCollection:
    """See `IRevisionCollection`."""

    implements(IRevisionCollection)

    def __init__(self, store=None, filter_expressions=None):
        self._store = store
        if filter_expressions is None:
            filter_expressions = []
        self._filter_expressions = filter_expressions

    @property
    def store(self):
        # Although you might think we could set the default value for store in
        # the constructor, we can't. The IStoreSelector utility is not
        # available at the time that the branchcollection.zcml is parsed,
        # which means we get an error if this code is in the constructor.
        if self._store is None:
            return getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        else:
            return self._store

    def _filterBy(self, expressions):
        return self.__class__(
            self.store,
            self._filter_expressions + expressions)

    def count(self):
        """See `IRevisionCollection`."""
        return self.getRevisions().count()

    def getRevisions(self):
        """See `IRevisionCollection`."""
        expressions = [RevisionCache.revision == Revision.id]
        expressions.extend(self._filter_expressions)
        result_set = self.store.find(Revision, expressions)
        result_set.config(distinct=True)
        return result_set
