# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Database implementation of the branch lookup utility."""

__metaclass__ = type
# This module doesn't export anything. If you want to lookup branches by name,
# then get the IBranchLookup utility.
__all__ = []

from zope.component import (
    adapts, getSiteManager, getUtility, queryMultiAdapter)
from zope.interface import implements

from storm.expr import Join
from sqlobject import SQLObjectNotFound

from canonical.config import config
from lp.code.model.branch import Branch
from lp.registry.model.distribution import Distribution
from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.person import Person
from lp.registry.model.product import Product
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.code.interfaces.branch import NoSuchBranch
from lp.code.interfaces.branchlookup import (
    CannotHaveLinkedBranch, IBranchLookup, ICanHasLinkedBranch,
    ILinkedBranchTraversable, ILinkedBranchTraverser, NoLinkedBranch)
from lp.code.interfaces.branchnamespace import (
    IBranchNamespaceSet, InvalidNamespace)
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distroseries import (
    IDistroSeries, IDistroSeriesSet)
from lp.registry.interfaces.pillar import IPillarNameSet
from lp.registry.interfaces.product import (
    InvalidProductName, IProduct, NoSuchProduct)
from lp.registry.interfaces.productseries import NoSuchProductSeries
from lp.registry.interfaces.sourcepackagename import (
    NoSuchSourcePackageName)
from canonical.launchpad.validators.name import valid_name
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)

from lazr.enum import DBItem
from lazr.uri import InvalidURIError, URI


def adapt(provided, interface):
    """Adapt 'obj' to 'interface', using multi-adapters if necessary."""
    required = interface(provided, None)
    if required is not None:
        return required
    try:
        return queryMultiAdapter(provided, interface)
    except TypeError:
        return None


class RootTraversable:
    """Root traversable for linked branch objects.

    Corresponds to '/' in the path. From here, you can traverse to a
    distribution or a product.
    """

    implements(ILinkedBranchTraversable)

    def traverse(self, name):
        """See `ITraversable`.

        :raise NoSuchProduct: If 'name' doesn't match an existing pillar.
        :return: `IPillar`.
        """
        if not valid_name(name):
            raise InvalidProductName(name)
        pillar = getUtility(IPillarNameSet).getByName(name)
        if pillar is None:
            # Actually, the pillar is no such *anything*. The user might be
            # trying to refer to a project, a distribution or a product. We
            # raise a NoSuchProduct error since that's what we used to raise
            # when we only supported product & junk branches.
            raise NoSuchProduct(name)
        return pillar


class _BaseTraversable:
    """Base class for traversable implementations.

    This just defines a very simple constructor.
    """

    def __init__(self, context):
        self.context = context


class ProductTraversable(_BaseTraversable):
    """Linked branch traversable for products.

    From here, you can traverse to a product series.
    """

    adapts(IProduct)
    implements(ILinkedBranchTraversable)

    def traverse(self, name):
        """See `ITraversable`.

        :raises NoSuchProductSeries: if 'name' doesn't match an existing
            series.
        :return: `IProductSeries`.
        """
        series = self.context.getSeries(name)
        if series is None:
            raise NoSuchProductSeries(name, self.context)
        return series


class DistributionTraversable(_BaseTraversable):
    """Linked branch traversable for distributions.

    From here, you can traverse to a distribution series.
    """

    adapts(IDistribution)
    implements(ILinkedBranchTraversable)

    def traverse(self, name):
        """See `ITraversable`."""
        # XXX: JonathanLange 2009-03-20 spec=package-branches bug=345737: This
        # could also try to find a package and then return a reference to its
        # development focus.
        return getUtility(IDistroSeriesSet).fromSuite(self.context, name)


class DistroSeriesTraversable:
    """Linked branch traversable for distribution series.

    From here, you can traverse to a source package.
    """

    adapts(IDistroSeries, DBItem)
    implements(ILinkedBranchTraversable)

    def __init__(self, distroseries, pocket):
        self.distroseries = distroseries
        self.pocket = pocket

    def traverse(self, name):
        """See `ITraversable`."""
        sourcepackage = self.distroseries.getSourcePackage(name)
        if sourcepackage is None:
            raise NoSuchSourcePackageName(name)
        return sourcepackage.getSuiteSourcePackage(self.pocket)


sm = getSiteManager()
sm.registerAdapter(ProductTraversable)
sm.registerAdapter(DistributionTraversable)
sm.registerAdapter(DistroSeriesTraversable)


class LinkedBranchTraverser:
    """Utility for traversing to objects that can have linked branches."""

    implements(ILinkedBranchTraverser)

    def traverse(self, path):
        """See `ILinkedBranchTraverser`."""
        segments = path.split('/')
        traversable = RootTraversable()
        while segments:
            name = segments.pop(0)
            context = traversable.traverse(name)
            traversable = adapt(context, ILinkedBranchTraversable)
            if traversable is None:
                break
        return context


class BranchLookup:
    """Utility for looking up branches."""

    implements(IBranchLookup)

    def get(self, branch_id, default=None):
        """See `IBranchLookup`."""
        try:
            return Branch.get(branch_id)
        except SQLObjectNotFound:
            return default

    @staticmethod
    def uriToUniqueName(uri):
        """See `IBranchLookup`."""
        schemes = ('http', 'sftp', 'bzr+ssh')
        codehosting_host = URI(config.codehosting.supermirror_root).host
        if uri.scheme in schemes and uri.host == codehosting_host:
            return uri.path.lstrip('/')
        else:
            return None

    def _uriHostAllowed(self, uri):
        """Is 'uri' for an allowed host?"""
        host = uri.host
        if host is None:
            host = ''
        allowed_hosts = set(config.codehosting.lp_url_hosts.split(','))
        return host in allowed_hosts

    def getByUrl(self, url):
        """See `IBranchLookup`."""
        if url is None:
            return None
        url = url.rstrip('/')
        try:
            uri = URI(url)
        except InvalidURIError:
            return None

        unique_name = self.uriToUniqueName(uri)
        if unique_name is not None:
            return self.getByUniqueName(unique_name)

        if uri.scheme == 'lp':
            if not self._uriHostAllowed(uri):
                return None
            try:
                return self.getByLPPath(uri.path.lstrip('/'))[0]
            except NoSuchBranch:
                return None

        return Branch.selectOneBy(url=url)

    def getByUniqueName(self, unique_name):
        """Find a branch by its unique name.

        For product branches, the unique name is ~user/product/branch; for
        source package branches,
        ~user/distro/distroseries/sourcepackagename/branch; for personal
        branches, ~user/+junk/branch.
        """
        # XXX: JonathanLange 2008-11-27 spec=package-branches: Doesn't handle
        # +dev alias.
        try:
            namespace_name, branch_name = unique_name.rsplit('/', 1)
        except ValueError:
            return None
        try:
            namespace_data = getUtility(IBranchNamespaceSet).parse(
                namespace_name)
        except InvalidNamespace:
            return None
        return self._getBranchInNamespace(namespace_data, branch_name)

    def _getBranchInNamespace(self, namespace_data, branch_name):
        if namespace_data['product'] == '+junk':
            return self._getPersonalBranch(
                namespace_data['person'], branch_name)
        elif namespace_data['product'] is None:
            return self._getPackageBranch(
                namespace_data['person'], namespace_data['distribution'],
                namespace_data['distroseries'],
                namespace_data['sourcepackagename'], branch_name)
        else:
            return self._getProductBranch(
                namespace_data['person'], namespace_data['product'],
                branch_name)

    def _getPersonalBranch(self, person, branch_name):
        """Find a personal branch given its path segments."""
        # Avoid circular imports.
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        origin = [Branch, Join(Person, Branch.owner == Person.id)]
        result = store.using(*origin).find(
            Branch, Person.name == person,
            Branch.distroseries == None,
            Branch.product == None,
            Branch.sourcepackagename == None,
            Branch.name == branch_name)
        branch = result.one()
        return branch

    def _getProductBranch(self, person, product, branch_name):
        """Find a product branch given its path segments."""
        # Avoid circular imports.
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        origin = [
            Branch,
            Join(Person, Branch.owner == Person.id),
            Join(Product, Branch.product == Product.id)]
        result = store.using(*origin).find(
            Branch, Person.name == person, Product.name == product,
            Branch.name == branch_name)
        branch = result.one()
        return branch

    def _getPackageBranch(self, owner, distribution, distroseries,
                          sourcepackagename, branch):
        """Find a source package branch given its path segments.

        Only gets unofficial source package branches, that is, branches with
        names like ~jml/ubuntu/jaunty/openssh/stuff.
        """
        # Avoid circular imports.
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        origin = [
            Branch,
            Join(Person, Branch.owner == Person.id),
            Join(SourcePackageName,
                 Branch.sourcepackagename == SourcePackageName.id),
            Join(DistroSeries,
                 Branch.distroseries == DistroSeries.id),
            Join(Distribution,
                 DistroSeries.distribution == Distribution.id)]
        result = store.using(*origin).find(
            Branch, Person.name == owner, Distribution.name == distribution,
            DistroSeries.name == distroseries,
            SourcePackageName.name == sourcepackagename,
            Branch.name == branch)
        branch = result.one()
        return branch

    def getByLPPath(self, path):
        """See `IBranchLookup`."""
        branch = suffix = None
        if not path.startswith('~'):
            # If the first element doesn't start with a tilde, then maybe
            # 'path' is a shorthand notation for a branch.
            result = getUtility(ILinkedBranchTraverser).traverse(path)
            branch = self._getLinkedBranch(result)
        else:
            namespace_set = getUtility(IBranchNamespaceSet)
            segments = iter(path.lstrip('~').split('/'))
            branch = namespace_set.traverse(segments)
            suffix =  '/'.join(segments)
            if not check_permission('launchpad.View', branch):
                raise NoSuchBranch(path)
            if suffix == '':
                suffix = None
        return branch, suffix

    def _getLinkedBranch(self, provided):
        """Get the linked branch for 'provided'.

        :raise CannotHaveLinkedBranch: If 'provided' can never have a linked
            branch.
        :raise NoLinkedBranch: If 'provided' could have a linked branch, but
            doesn't.
        :return: The linked branch, an `IBranch`.
        """
        has_linked_branch = adapt(provided, ICanHasLinkedBranch)
        if has_linked_branch is None:
            raise CannotHaveLinkedBranch(provided)
        branch = has_linked_branch.branch
        if branch is None:
            raise NoLinkedBranch(provided)
        if not check_permission('launchpad.View', branch):
            raise NoLinkedBranch(provided)
        return branch
