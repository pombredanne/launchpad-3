# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Branch contexts."""

__metaclass__ = type
__all__ = [
    'JunkContext',
    'PackageContext',
    ]

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces.branchcontext import IBranchContext
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)


class JunkContext:
    implements(IBranchContext)

    name = '+junk'

    def __init__(self, person):
        self.person = person

    def getBranches(self):
        from canonical.launchpad.database import Branch
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(
            Branch, Branch.owner == self.person, Branch.product == None,
            Branch.distroseries == None, Branch.sourcepackagename == None)


class PackageContext:
    implements(IBranchContext)

    def __init__(self, distroseries, sourcepackagename):
        self.distroseries = distroseries
        self.sourcepackagename = sourcepackagename

    def getBranches(self):
        from canonical.launchpad.database import Branch
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(
            Branch, Branch.distroseries == self.distroseries,
            Branch.sourcepackagename == self.sourcepackagename)

    @property
    def name(self):
        return '%s/%s/%s' % (
            self.distroseries.distribution.name,
            self.distroseries.name,
            self.sourcepackagename.name)
