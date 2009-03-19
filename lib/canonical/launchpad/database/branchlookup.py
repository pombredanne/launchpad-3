# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Database implementation of the branch lookup utility."""

__metaclass__ = type
# This module doesn't export anything. If you want to lookup branches by name,
# then get the IBranchLookup utility.
__all__ = []

from zope.component import getUtility
from zope.interface import implements

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
    IBranchLookup, InvalidBranchIdentifier, NoBranchForSeries,
    NoDefaultBranch)
from canonical.launchpad.interfaces.branchnamespace import (
    IBranchNamespaceSet, InvalidNamespace)
from canonical.launchpad.interfaces.distribution import IDistribution
from canonical.launchpad.interfaces.distroseries import IDistroSeries
from canonical.launchpad.interfaces.pillar import IPillarNameSet
from canonical.launchpad.interfaces.product import (
    InvalidProductName, IProduct, NoSuchProduct)
from canonical.launchpad.interfaces.productseries import (
    IProductSeries, NoSuchProductSeries)
from canonical.launchpad.interfaces.project import IProject
from canonical.launchpad.interfaces.publishing import PackagePublishingPocket
from canonical.launchpad.interfaces.sourcepackage import ISourcePackage
from canonical.launchpad.validators.name import valid_name
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)

from lazr.uri import InvalidURIError, URI


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
        # +dev alias, nor official source package branches.
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

    def _getByPath(self, path):
        """Given a path within a branch, return the branch and the path."""
        namespace_set = getUtility(IBranchNamespaceSet)
        if not path.startswith('~'):
            raise InvalidNamespace(path)
        segments = iter(path.lstrip('~').split('/'))
        branch = namespace_set.traverse(segments)
        return branch, '/'.join(segments)

    def getByLPPath(self, path):
        """See `IBranchLookup`."""
        # XXX: It's kind of shitty that this returns series -- it's just a
        # trick to let us raise convincing errors if the branch is private.
        # There's got to be a better way -- perhaps a property on branch that
        # points to the relevant object?
        branch = suffix = series = None
        try:
            branch, suffix = self._getByPath(path)
            if suffix == '':
                suffix = None
        except InvalidNamespace:
            # If the first element doesn't start with a tilde, then maybe
            # 'path' is a shorthand notation for a branch.
            branch, series = self._getDefaultProductBranch(path)
        return branch, suffix, series

    def _traverseToShortcut(self, path):
        segments = iter(path.split('/'))
        pillar_name = segments.next()
        if not valid_name(pillar_name):
            raise InvalidProductName(pillar_name)
        pillar = getUtility(IPillarNameSet).getByName(pillar_name)
        if pillar is None:
            raise NoSuchProduct(pillar_name)
        try:
            series_name = segments.next()
        except StopIteration:
            return pillar
        series = pillar.getSeries(series_name)
        if series is None:
            raise NoSuchProductSeries(series_name, pillar)
        if IProductSeries.providedBy(series):
            try:
                segments.next()
            except StopIteration:
                return series
        elif IDistroSeries.providedBy(series):
            try:
                sourcepackagename = segments.next()
            except StopIteration:
                raise NoDefaultBranch(series, 'distribution series')
            sourcepackage = series.getSourcePackage(sourcepackagename)
            #if sourcepackage is None:
            #    raise NoSuchSourcePackageName(sourcepackagename)
            return sourcepackage
        raise InvalidBranchIdentifier(path)

    def _getBranchAndSeriesForObject(self, obj):
        # XXX: This should be a series of adapters.
        if IProduct.providedBy(obj):
            return obj.development_focus.series_branch, obj.development_focus
        if IProductSeries.providedBy(obj):
            return obj.series_branch, obj
        if ISourcePackage.providedBy(obj):
            return obj.getBranch(PackagePublishingPocket.RELEASE), None
        if IProject.providedBy(obj):
            raise NoDefaultBranch(obj, 'project group')
        if IDistribution.providedBy(obj):
            raise NoDefaultBranch(obj, 'distribution')
        raise NoDefaultBranch(obj, 'unknown')

    def _getDefaultProductBranch(self, path):
        """Return the branch with the shortcut 'path'.

        :param path: A shortcut to a branch.
        :raise InvalidBranchIdentifier: if 'path' has too many segments to be
            a shortcut.
        :raise InvalidProductIdentifier: if 'path' starts with an invalid
            name for a product.
        :raise NoSuchProduct: if 'path' starts with a non-existent product.
        :raise NoSuchSeries: if 'path' refers to a product series and that
            series does not exist.
        :raise NoBranchForSeries: if 'path' refers to a product series that
            exists, but does not have a branch.
        :return: The branch.
        """
        result = self._traverseToShortcut(path)
        branch, series = self._getBranchAndSeriesForObject(result)
        if branch is None:
            raise NoBranchForSeries(series)
        return branch, series
