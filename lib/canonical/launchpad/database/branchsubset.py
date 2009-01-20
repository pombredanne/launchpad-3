# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type
__all__ = [
    'ProductBranchSubset',
    ]

from zope.interface import implements

from canonical.launchpad.interfaces.branchsubset import IBranchSubset


class ProductBranchSubset:

    implements(IBranchSubset)

    def __init__(self, product):
        pass
