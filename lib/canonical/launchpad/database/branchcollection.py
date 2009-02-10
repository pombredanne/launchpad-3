# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Implementations of `IBranchCollection`."""

__metaclass__ = type
__all__ = [
    'GenericBranchCollection',
    'PersonBranchCollection',
    'ProductBranchCollection',
    ]

from zope.interface import implements

from canonical.launchpad.database.branch import Branch
from canonical.launchpad.interfaces.branchcollection import IBranchCollection


class GenericBranchCollection:

    implements(IBranchCollection)

    def __init__(self, store, branch_filter_expr=None, name=None,
                 displayname=None):
        self._store = store
        self._branch_filter_expr = branch_filter_expr
        self.name = name
        self.displayname = displayname

    def getBranches(self):
        expression = self._branch_filter_expr
        if expression is None:
            return self._store.find(Branch)
        else:
            return self._store.find(Branch, expression)

    @property
    def count(self):
        return self.getBranches().count()
