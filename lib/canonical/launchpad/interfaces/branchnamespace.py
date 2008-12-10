# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Interface for a branch namespace."""

__metaclass__ = type
__all__ = [
    'get_branch_namespace',
    'IBranchNamespace',
    'IBranchNamespaceSet',
    'InvalidNamespace',
    'lookup_branch_namespace',
    ]

from zope.component import getUtility
from zope.interface import Interface, Attribute

from canonical.launchpad.interfaces.branch import BranchLifecycleStatus
from canonical.launchpad.interfaces.distribution import (
    IDistributionSet, NoSuchDistribution)
from canonical.launchpad.interfaces.distroseries import (
    IDistroSeriesSet, NoSuchDistroSeries)
from canonical.launchpad.interfaces.person import IPersonSet, NoSuchPerson
from canonical.launchpad.interfaces.product import IProductSet, NoSuchProduct
from canonical.launchpad.interfaces.sourcepackagename import (
    ISourcePackageNameSet)


class IBranchNamespace(Interface):
    """A namespace that a branch lives in."""

    owner = Attribute(
        "The `IPerson` who owns this namespace. Their name normally appears "
        "in the namespace's name.")
    name = Attribute(
        "The name of the namespace. This is prepended to the branch name.")

    def createBranch(branch_type, name, registrant, url=None, title=None,
                     lifecycle_status=BranchLifecycleStatus.NEW, summary=None,
                     whiteboard=None):
        """Create and return an `IBranch` in this namespace."""

    def createBranchWithPrefix(branch_type, prefix, registrant, url=None):
        """Create and return an `IBranch` with a name starting with 'prefix'.

        Use this method to automatically create a branch with an inferred
        name.
        """

    def findUnusedName(prefix):
        """Find an unused branch name starting with 'prefix'.

        Note that there is no guarantee that the name returned by this method
        will remain unused for very long. If you wish to create a branch with
        a given prefix, use createBranchWithPrefix.
        """

    def getBranches():
        """Return the branches in this namespace."""

    def getBranchName(name):
        """Get the potential unique name for a branch called 'name'."""

    def getByName(name, default=None):
        """Find the branch in this namespace called 'name'.

        :return: `IBranch` if found, 'default' if not.
        """

    def isNameUsed(name):
        """Is 'name' already used in this namespace?"""


class IBranchNamespaceSet(Interface):
    """Interface for getting branch namespaces.

    This interface exists *solely* to avoid importing things from the
    'database' package. Use `get_branch_namespace` to get branch namespaces
    instead.
    """

    def get(person, product, distroseries, sourcepackagename):
        """Return the appropriate `IBranchNamespace` for the given objects."""


def get_branch_namespace(person, product=None, distroseries=None,
                         sourcepackagename=None):
    return getUtility(IBranchNamespaceSet).get(
        person, product, distroseries, sourcepackagename)


class InvalidNamespace(Exception):
    """Raised when someone tries to lookup a namespace with a bad name.

    By 'bad', we mean that the name is unparseable. It might be too short, too
    long or malformed in some other way.
    """

    def __init__(self, name):
        self.name = name
        Exception.__init__(
            self, "Cannot understand namespace name: '%s'" % (name,))


def lookup_branch_namespace(namespace_name):
    tokens = iter(namespace_name.split('/'))
    person_name = tokens.next()
    if not person_name.startswith('~'):
        raise InvalidNamespace(namespace_name)
    person_name = person_name[1:]
    person = getUtility(IPersonSet).getByName(person_name)
    if person is None:
        raise NoSuchPerson(person_name)
    try:
        product_name = tokens.next()
    except StopIteration:
        raise InvalidNamespace(namespace_name)
    product = distribution = distroseries = sourcepackagename = None
    if product_name == '+junk':
        product = None
    else:
        product = getUtility(IProductSet).getByName(product_name)
        if product is None:
            try:
                distroseries_name = tokens.next()
            except StopIteration:
                raise NoSuchProduct(product_name)
            distribution = getUtility(IDistributionSet).getByName(
                product_name)
            if distribution is None:
                raise NoSuchDistribution(product_name)
            distroseries = getUtility(IDistroSeriesSet).queryByName(
                distribution, distroseries_name)
            if distroseries is None:
                raise NoSuchDistroSeries(distroseries_name)
            try:
                sourcepackagename_name = tokens.next()
            except StopIteration:
                raise InvalidNamespace(namespace_name)
            sourcepackagename = getUtility(ISourcePackageNameSet)[
                sourcepackagename_name]
    try:
        tokens.next()
    except StopIteration:
        pass
    else:
        raise InvalidNamespace(namespace_name)
    return get_branch_namespace(
        person, product=product, distroseries=distroseries,
        sourcepackagename=sourcepackagename)
