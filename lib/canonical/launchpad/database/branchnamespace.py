# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Implementations of `IBranchNamespace`."""

__metaclass__ = type
__all__ = [
    'get_namespace',
    'PackageNamespace',
    'PersonalNamespace',
    'ProductNamespace',
    ]

from storm.locals import And

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.database import Branch
from canonical.launchpad.interfaces.branch import (
    BranchLifecycleStatus, IBranchSet)
from canonical.launchpad.interfaces.branchnamespace import IBranchNamespace
from canonical.launchpad.webapp.interfaces import (
        IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)


class _BaseNamespace:
    """Common code for branch namespaces."""

    def createBranch(self, branch_type, name, registrant, url=None,
                     title=None, lifecycle_status=BranchLifecycleStatus.NEW,
                     summary=None, whiteboard=None, date_created=None,
                     branch_format=None, repository_format=None,
                     control_format=None):
        """See `IBranchNamespace`."""
        owner = self.owner
        product = getattr(self, 'product', None)
        distroseries = getattr(self, 'distroseries', None)
        sourcepackagename = getattr(self, 'sourcepackagename', None)
        return getUtility(IBranchSet).new(
            branch_type, name, registrant, owner, product, url=url,
            title=title, lifecycle_status=lifecycle_status, summary=summary,
            whiteboard=whiteboard, date_created=date_created,
            branch_format=branch_format, repository_format=repository_format,
            control_format=control_format, distroseries=distroseries,
            sourcepackagename=sourcepackagename)

    def createBranchWithPrefix(self, branch_type, prefix, registrant,
                               url=None):
        """See `IBranchNamespace`."""
        name = self.findUnusedName(prefix)
        return self.createBranch(branch_type, name, registrant, url=url)

    def findUnusedName(self, prefix):
        """See `IBranchNamespace`."""
        name = prefix
        count = 0
        while self.isNameUsed(name):
            count += 1
            name = "%s-%s" % (prefix, count)
        return name

    def getBranches(self):
        """See `IBranchNamespace`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(Branch, self._getBranchesClause())

    def getBranchName(self, branch_name):
        """See `IBranchNamespace`."""
        return '%s/%s' % (self.name, branch_name)

    def getByName(self, branch_name, default=None):
        """See `IBranchNamespace`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        match = store.find(
            Branch, self._getBranchesClause(),
            Branch.name == branch_name).one()
        if match is None:
            match = default
        return match

    def isNameUsed(self, branch_name):
        return self.getByName(branch_name) is not None


class PersonalNamespace(_BaseNamespace):
    """A namespace for personal (or 'junk') branches.

    Branches in this namespace have names like '~foo/+junk/bar'.
    """

    implements(IBranchNamespace)

    def __init__(self, person):
        self.owner = person

    def _getBranchesClause(self):
        return And(
            Branch.owner == self.owner, Branch.product == None,
            Branch.distroseries == None, Branch.sourcepackagename == None)

    @property
    def name(self):
        """See `IBranchNamespace`."""
        return '~%s/+junk' % (self.owner.name,)


class ProductNamespace(_BaseNamespace):
    """A namespace for product branches.

    This namespace is for all the branches owned by a particular person in a
    particular product.
    """

    implements(IBranchNamespace)

    def __init__(self, person, product):
        self.owner = person
        self.product = product

    def _getBranchesClause(self):
        return And(Branch.owner == self.owner, Branch.product == self.product)

    @property
    def name(self):
        """See `IBranchNamespace`."""
        return '~%s/%s' % (self.owner.name, self.product.name)


class PackageNamespace(_BaseNamespace):
    """A namespace for source package branches.

    This namespace is for all the branches owned by a particular person in a
    particular source package in a particular distroseries.
    """

    implements(IBranchNamespace)

    def __init__(self, person, distroseries, sourcepackagename):
        self.owner = person
        self.distroseries = distroseries
        self.sourcepackagename = sourcepackagename

    def _getBranchesClause(self):
        return And(
            Branch.owner == self.owner,
            Branch.distroseries == self.distroseries,
            Branch.sourcepackagename == self.sourcepackagename)

    @property
    def name(self):
        """See `IBranchNamespace`."""
        return '~%s/%s/%s/%s' % (
            self.owner.name, self.distroseries.distribution.name,
            self.distroseries.name, self.sourcepackagename.name)


class BranchNamespaceSet:
    """Only implementation of `IBranchNamespaceSet`."""

    def get(self, person, product=None, distroseries=None,
            sourcepackagename=None):
        """See `IBranchNamespaceSet`."""
        if product is not None:
            assert (distroseries is None and sourcepackagename is None), (
                "product implies no distroseries or sourcepackagename. "
                "Got %r, %r, %r."
                % (product, distroseries, sourcepackagename))
            return ProductNamespace(person, product)
        elif distroseries is not None:
            assert sourcepackagename is not None, (
                "distroseries implies sourcepackagename. Got %r, %r"
                % (distroseries, sourcepackagename))
            return PackageNamespace(person, distroseries, sourcepackagename)
        else:
            return PersonalNamespace(person)
