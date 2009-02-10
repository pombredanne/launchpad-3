# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Implementations of `IBranchCollection`."""

__metaclass__ = type
__all__ = [
    'GenericBranchCollection',
    'PersonBranchCollection',
    'ProductBranchCollection',
    ]

from datetime import datetime, timedelta

import pytz
from storm.locals import And, Desc, Store
from zope.interface import implements

from canonical.launchpad.database.branch import Branch
from canonical.launchpad.database.branchrevision import BranchRevision
from canonical.launchpad.database.revision import Revision
from canonical.launchpad.interfaces.branchcollection import IBranchCollection


def revision_time_limit(day_limit):
    """The storm fragment to limit the revision_date field of the Revision."""
    now = datetime.now(pytz.UTC)
    earliest = now - timedelta(days=day_limit)

    return And(
        Revision.revision_date <= now,
        Revision.revision_date > earliest)


class GenericBranchCollection:

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


class ProductBranchCollection(GenericBranchCollection):

    implements(IBranchCollection)

    def __init__(self, product):
        store = Store.of(product)
        expression = (Branch.product == product)
        super(ProductBranchCollection, self).__init__(
            store, expression, product.name, product.displayname)

    def getRevisions(self, days=30):
        # XXX: The '30' bit is untested.

        # XXX: The version in revision.py uses a subselect and
        # BranchRevision.revision >= revision_subselect. We don't need it yet
        # to make the tests pass.
        result_set = self._store.find(
            Revision,
            revision_time_limit(days),
            BranchRevision.revision == Revision.id,
            BranchRevision.branch == Branch.id,
            self._branch_filter_expr,
            Branch.private == False)
        result_set.config(distinct=True)
        return result_set.order_by(Desc(Revision.revision_date))


class PersonBranchCollection:

    implements(IBranchCollection)

    def __init__(self, person):
        self._store = Store.of(person)
        self._person = person
        self.name = person.name
        self.displayname = person.displayname

    @property
    def count(self):
        return self.getBranches().count()

    def getBranches(self):
        return self._store.find(Branch, Branch.owner == self._person)

    def getRevisions(self, days=30):
        # XXX: This is all revisions in any branch owned by the person. I
        # think we almost never want this, and instead want all revisions
        # authored by a person.
        result_set = self._store.find(
            Revision,
            revision_time_limit(days),
            BranchRevision.revision == Revision.id,
            BranchRevision.branch == Branch.id,
            Branch.owner == self._person,
            Branch.private == False)
        result_set.config(distinct=True)
        return result_set.order_by(Desc(Revision.revision_date))
