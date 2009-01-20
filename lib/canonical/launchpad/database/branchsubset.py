# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type
__all__ = [
    'PersonBranchSubset',
    'ProductBranchSubset',
    ]

from storm.locals import Store

from zope.interface import implements

from canonical.launchpad.database.branch import Branch
from canonical.launchpad.interfaces.branchsubset import IBranchSubset


class ProductBranchSubset:

    implements(IBranchSubset)

    def __init__(self, product):
        self._store = Store.of(product)
        self._product = product
        self.name = product.name
        self.displayname = product.displayname

    @property
    def count(self):
        # XXX: Is 'count' the best name for this? - jml
        return self.getBranches().count()

    def getBranches(self):
        return self._store.find(Branch, Branch.product == self._product)


class PersonBranchSubset:

    implements(IBranchSubset)

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
