# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Implementations of `IBranchCollection`."""

__metaclass__ = type
__all__ = [
    'GenericBranchCollection',
    ]

from storm.expr import And, Or

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.database.branch import Branch
from canonical.launchpad.interfaces import ILaunchpadCelebrities
from canonical.launchpad.interfaces.branchcollection import IBranchCollection
from canonical.launchpad.interfaces.codehosting import LAUNCHPAD_SERVICES


class GenericBranchCollection:
    """See `IBranchCollection`."""

    implements(IBranchCollection)

    def __init__(self, store, branch_filter_expressions=None, name=None,
                 displayname=None):
        self._store = store
        if branch_filter_expressions is None:
            branch_filter_expressions = []
        self._branch_filter_expressions = branch_filter_expressions
        self.name = name
        self.displayname = displayname

    @property
    def count(self):
        """See `IBranchCollection`."""
        return self.getBranches().count()

    def getBranches(self):
        """See `IBranchCollection`."""
        return self._store.find(Branch, *(self._branch_filter_expressions))

    def inProduct(self, product):
        """See `IBranchCollection`."""
        expression = (
            self._branch_filter_expressions + [Branch.product == product])
        return self.__class__(
            self._store, expression, name=self.name,
            displayname=self.displayname)

    def ownedBy(self, person):
        """See `IBranchCollection`."""
        # XXX: duplicate of inProduct code -- refactor
        expression = (
            self._branch_filter_expressions + [Branch.owner == person])
        return self.__class__(
            self._store, expression, name=self.name,
            displayname=self.displayname)

    def visibleByUser(self, person):
        """See `IBranchCollection`."""
        if person is None:
            expression = [Or(Branch.private == False, Branch.owner == person)]
        elif person == LAUNCHPAD_SERVICES:
            return self
        elif person.inTeam(getUtility(ILaunchpadCelebrities).admin):
            return self
        elif person.inTeam(getUtility(ILaunchpadCelebrities).bazaar_experts):
            return self
        else:
            expression = [Or(Branch.private == False, Branch.owner == person)]
        expression += self._branch_filter_expressions
        return self.__class__(
            self._store, expression, name=self.name,
            displayname=self.displayname)
