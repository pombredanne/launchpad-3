# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Implementations of `IBranchCollection`."""

__metaclass__ = type
__all__ = [
    'GenericBranchCollection',
    ]

from storm.expr import And, LeftJoin, Join, Or, Select
from storm.info import ClassAlias

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet)
from canonical.launchpad.database.branch import Branch
from canonical.launchpad.database.branchsubscription import BranchSubscription
from canonical.launchpad.database.person import Person
from canonical.launchpad.database.product import Product
from canonical.launchpad.database.teammembership import TeamParticipation
from canonical.launchpad.interfaces.branch import (
    user_has_special_branch_access)
from canonical.launchpad.interfaces.branchcollection import IBranchCollection
from canonical.launchpad.interfaces.codehosting import LAUNCHPAD_SERVICES
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)


class GenericBranchCollection:
    """See `IBranchCollection`."""

    implements(IBranchCollection)

    def __init__(self, store=None, branch_filter_expressions=None,
                 tables=None):
        self._store = store
        if branch_filter_expressions is None:
            branch_filter_expressions = []
        self._branch_filter_expressions = branch_filter_expressions
        if tables is None:
            # Join in Product and the Person table as 'Owner' so that we can
            # sort the results by product name and owner name.
            Owner = ClassAlias(Person, 'Owner')
            tables = [Branch, LeftJoin(Product, Branch.product == Product.id),
                      Join(Owner, Branch.owner == Owner.id)]
        self._tables = tables

    def count(self):
        """See `IBranchCollection`."""
        return self.getBranches().count()

    def _filterBy(self, tables, *expressions):
        """Return a subset of this collection, filtered by 'expressions'."""
        # XXX: JonathanLange 2009-02-17: We might be able to avoid the need
        # for explicit 'tables' by harnessing Storm's table inference system.
        # See http://paste.ubuntu.com/118711/ for one way to do that.
        return self.__class__(
            self._store, self._branch_filter_expressions + list(expressions),
            self._tables + tables)

    def getBranches(self):
        """See `IBranchCollection`."""
        # XXX: JonathanLange 2009-02-17: Although you might think we could set
        # the default value for store in the constructor, we can't. The
        # IStoreSelector utility is not available at the time that the
        # branchcollection.zcml is parsed, which means we get an error if this
        # code is in the constructor.
        if self._store is None:
            store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        else:
            store = self._store
        results = store.using(*(self._tables)).find(
            Branch, *(self._branch_filter_expressions))
        def identity(x):
            return x
        # Decorate the result set to work around bug 217644.
        return DecoratedResultSet(results, identity)

    def inProduct(self, product):
        """See `IBranchCollection`."""
        return self._filterBy([], Branch.product == product)

    def inProject(self, project):
        """See `IBranchCollection`."""
        return self._filterBy(
            [], Product.project == project.id)

    def inSourcePackage(self, source_package):
        """See `IBranchCollection`."""
        return self._filterBy(
            [], Branch.distroseries == source_package.distroseries,
            Branch.sourcepackagename == source_package.sourcepackagename)

    def ownedBy(self, person):
        """See `IBranchCollection`."""
        return self._filterBy([], Branch.owner == person)

    def registeredBy(self, person):
        """See `IBranchCollection`."""
        return self._filterBy([], Branch.registrant == person)

    def relatedTo(self, person):
        """See `IBranchCollection`."""
        return self._filterBy(
            [LeftJoin(
                BranchSubscription,
                BranchSubscription.branch == Branch.id)],
            Or(Branch.owner == person,
               Branch.registrant == person,
               BranchSubscription.person == person))

    def subscribedBy(self, person):
        """See `IBranchCollection`."""
        return self._filterBy(
            [Join(BranchSubscription,
                  BranchSubscription.branch == Branch.id)],
            BranchSubscription.person == person)

    def visibleByUser(self, person):
        """See `IBranchCollection`."""
        if (person == LAUNCHPAD_SERVICES or
            user_has_special_branch_access(person)):
            return self
        # Do this in a sub-query to avoid making the main query a DISTINCT
        # one, which would make sorting and the like harder.
        visible_branches = Select(
            Branch.id,
            Or(Branch.private == False,
               And(Branch.owner == TeamParticipation.teamID,
                   TeamParticipation.person == person),
               And(BranchSubscription.branch == Branch.id,
                   BranchSubscription.person == TeamParticipation.teamID,
                   TeamParticipation.person == person)),
            distinct=True)
        return self._filterBy([], Branch.id.is_in(visible_branches))

    def withLifecycleStatus(self, *statuses):
        """See `IBranchCollection`."""
        return self._filterBy([], Branch.lifecycle_status.is_in(statuses))
