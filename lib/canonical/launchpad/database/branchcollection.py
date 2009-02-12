# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Implementations of `IBranchCollection`."""

__metaclass__ = type
__all__ = [
    'GenericBranchCollection',
    ]

from storm.expr import And, Or

from zope.interface import implements

from canonical.launchpad.database.branch import Branch
from canonical.launchpad.database.branchsubscription import BranchSubscription
from canonical.launchpad.database.teammembership import TeamParticipation
from canonical.launchpad.interfaces.branch import (
    user_has_special_branch_access)
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

    def filterBy(self, *expressions):
        """Return a subset of this collection, filtered by 'expressions'."""
        return self.__class__(
            self._store, self._branch_filter_expressions + list(expressions),
            name=self.name, displayname=self.displayname)

    def getBranches(self):
        """See `IBranchCollection`."""
        return self._store.find(
            Branch, *(self._branch_filter_expressions)).config(distinct=True)

    def inProduct(self, product):
        """See `IBranchCollection`."""
        return self.filterBy(Branch.product == product)

    def ownedBy(self, person):
        """See `IBranchCollection`."""
        return self.filterBy(Branch.owner == person)

    def registeredBy(self, person):
        """See `IBranchCollection`."""
        return self.filterBy(Branch.registrant == person)

    def visibleByUser(self, person):
        """See `IBranchCollection`."""
        if (person == LAUNCHPAD_SERVICES or
            user_has_special_branch_access(person)):
            return self
        return self.filterBy(
            Or(Branch.private == False,
               And(Branch.owner == TeamParticipation.teamID,
                   TeamParticipation.person == person),
               And(BranchSubscription.branch == Branch.id,
                   BranchSubscription.person == TeamParticipation.teamID,
                   TeamParticipation.person == person)))

    def withLifecycleStatus(self, *statuses):
        """See `IBranchCollection`."""
        return self.filterBy(Branch.lifecycle_status.is_in(statuses))
