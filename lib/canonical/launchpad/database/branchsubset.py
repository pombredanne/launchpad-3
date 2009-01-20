# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type
__all__ = [
    'PersonBranchSubset',
    'ProductBranchSubset',
    ]

from zope.interface import implements

from canonical.launchpad.interfaces.branchsubset import IBranchSubset


class ProductBranchSubset:

    implements(IBranchSubset)

    def __init__(self, product):
        self.name = product.name
        self.displayname = product.displayname


class PersonBranchSubset:

    implements(IBranchSubset)

    def __init__(self, person):
        self.name = person.name
        self.displayname = person.displayname
