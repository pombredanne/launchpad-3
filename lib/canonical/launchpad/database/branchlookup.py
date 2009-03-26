# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Database implementation of the branch lookup utility."""

__metaclass__ = type
# This module doesn't export anything. If you want to lookup branches by name,
# then get the IBranchLookup utility.
__all__ = []

from zope.component import (
    adapter, adapts, getSiteManager, getUtility, queryMultiAdapter)
from zope.interface import classProvides, implementer, implements

from storm.expr import Join
from sqlobject import SQLObjectNotFound

from canonical.config import config
from canonical.launchpad.database.branch import Branch
from canonical.launchpad.database.distribution import Distribution
from canonical.launchpad.database.distroseries import DistroSeries
from canonical.launchpad.database.person import Person
from canonical.launchpad.database.product import Product
from canonical.launchpad.database.sourcepackagename import SourcePackageName
from canonical.launchpad.interfaces.branch import NoSuchBranch
from canonical.launchpad.interfaces.branchlookup import (
    CannotHaveLinkedBranch, IBranchLookup, ICanHasLinkedBranch,
    ILinkedBranchTraversable, ILinkedBranchTraverser, ISourcePackagePocket,
    ISourcePackagePocketFactory, NoLinkedBranch)
from canonical.launchpad.interfaces.branchnamespace import (
    IBranchNamespaceSet, InvalidNamespace)
from canonical.launchpad.interfaces.distribution import IDistribution
from canonical.launchpad.interfaces.distroseries import (
    IDistroSeries, IDistroSeriesSet)
from canonical.launchpad.interfaces.pillar import IPillarNameSet
from canonical.launchpad.interfaces.product import (
    InvalidProductName, IProduct, NoSuchProduct)
from canonical.launchpad.interfaces.productseries import (
    IProductSeries, NoSuchProductSeries)
from canonical.launchpad.interfaces.publishing import PackagePublishingPocket
from canonical.launchpad.interfaces.sourcepackagename import (
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

    def traverse(self, name, further_path):
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

    def traverse(self, name, further_path):
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

    def traverse(self, name, further_path):
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

    def traverse(self, name, further_path):
        """See `ITraversable`."""
        sourcepackage = self.distroseries.getSourcePackage(name)
        if sourcepackage is None:
            raise NoSuchSourcePackageName(name)
        return getUtility(ISourcePackagePocketFactory).new(
            sourcepackage, self.pocket)


class HasLinkedBranch:
    """A thing that has a linked branch."""

    implements(ICanHasLinkedBranch)

    def __init__(self, branch):
        self.branch = branch


@adapter(IProductSeries)
@implementer(ICanHasLinkedBranch)
def product_series_linked_branch(product_series):
    """The series branch of a product series is its linked branch."""
    return HasLinkedBranch(product_series.series_branch)


@adapter(IProduct)
@implementer(ICanHasLinkedBranch)
def product_linked_branch(product):
    """The series branch of a product's development focus is its branch."""
    return HasLinkedBranch(product.development_focus.series_branch)


sm = getSiteManager()
sm.registerAdapter(ProductTraversable)
sm.registerAdapter(DistributionTraversable)
sm.registerAdapter(DistroSeriesTraversable)
sm.registerAdapter(product_series_linked_branch)
sm.registerAdapter(product_linked_branch)


class LinkedBranchTraverser:
    """Utility for traversing to objects that can have linked branches."""

    implements(ILinkedBranchTraverser)

    def traverse(self, path):
        """See `ILinkedBranchTraverser`."""
        segments = path.split('/')
        traversable = RootTraversable()
        while segments:
            name = segments.pop(0)
            context = traversable.traverse(name, segments)
            traversable = adapt(context, ILinkedBranchTraversable)
            if traversable is None:
                break
        return context


class SourcePackagePocket:
    """A source package and a pocket.

    This exists to provide a consistent interface for the error condition of
    users looking up official branches for the pocket of a source package
    where no such linked branch exists. All of the other "no linked branch"
    cases have a single object for which there is no linked branch -- this is
    the equivalent for source packages.
    """

    implements(ISourcePackagePocket)
    classProvides(ISourcePackagePocketFactory)

    def __init__(self, sourcepackage, pocket):
        self.sourcepackage = sourcepackage
        self.pocket = pocket

    @classmethod
    def new(cls, package, pocket):
        """See `ISourcePackagePocketFactory`."""
        return cls(package, pocket)

    def __eq__(self, other):
        """See `ISourcePackagePocket`."""
        try:
            other = ISourcePackagePocket(other)
        except TypeError:
            return NotImplemented
        return (
            self.sourcepackage == other.sourcepackage
            and self.pocket == other.pocket)

    def __ne__(self, other):
        """See `ISourcePackagePocket`."""
        return not (self == other)

    @property
    def displayname(self):
        """See `ISourcePackagePocket`."""
        return self.path

    @property
    def branch(self):
        """See `ISourcePackagePocket`."""
        return self.sourcepackage.getBranch(self.pocket)

    @property
    def path(self):
        """See `ISourcePackagePocket`."""
        return '%s/%s/%s' % (
            self.sourcepackage.distribution.name,
            self.suite,
            self.sourcepackage.name)

    @property
    def suite(self):
        """See `ISourcePackagePocket`."""
        distroseries = self.sourcepackage.distroseries.name
        if self.pocket == PackagePublishingPocket.RELEASE:
            return distroseries
        else:
            return '%s-%s' % (distroseries, self.pocket.name.lower())


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
        assert not url.endswith('/')
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
