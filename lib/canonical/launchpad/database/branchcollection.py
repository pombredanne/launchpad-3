# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Implementations of `IBranchCollection`."""

__metaclass__ = type
__all__ = [
    'GenericBranchCollection',
    ]

from storm.expr import Or

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

    def filterBy(self, *expressions):
        """Return a subset of this collection, filtered by 'expressions'."""
        return self.__class__(
            self._store, self._branch_filter_expressions + list(expressions),
            name=self.name, displayname=self.displayname)

    @property
    def count(self):
        """See `IBranchCollection`."""
        return self.getBranches().count()

    def getBranches(self):
        """See `IBranchCollection`."""
        return self._store.find(Branch, *(self._branch_filter_expressions))

    def inProduct(self, product):
        """See `IBranchCollection`."""
        return self.filterBy(Branch.product == product)

    def ownedBy(self, person):
        """See `IBranchCollection`."""
        # XXX: duplicate of inProduct code -- refactor
        return self.filterBy(Branch.owner == person)

    def visibleByUser(self, person):
        """See `IBranchCollection`."""
        celebrities = getUtility(ILaunchpadCelebrities)
        if person is not None and (
            person == LAUNCHPAD_SERVICES or
            person.inTeam(celebrities.admin) or
            person.inTeam(celebrities.bazaar_experts)):
            return self
        return self.filterBy(
            Or(Branch.private == False, Branch.owner == person))
