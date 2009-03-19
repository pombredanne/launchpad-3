# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Database implementation of the branch lookup utility."""

__metaclass__ = type
__all__ = []

from zope.component import getUtility
from zope.interface import implements

from storm.expr import Join
from sqlobject import SQLObjectNotFound

from canonical.config import config
from canonical.launchpad.database.branch import Branch
from canonical.launchpad.interfaces.branch import NoSuchBranch
from canonical.launchpad.interfaces.branchlookup import (
    IBranchLookup, InvalidBranchIdentifier, NoBranchForSeries)
from canonical.launchpad.interfaces.branchnamespace import (
    IBranchNamespaceSet, InvalidNamespace)
from canonical.launchpad.interfaces.product import (
    InvalidProductName, IProductSet, NoSuchProduct)
from canonical.launchpad.interfaces.productseries import NoSuchProductSeries
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

    def getByUrl(self, url, default=None):
        """See `IBranchLookup`."""
        assert not url.endswith('/')
        try:
            uri = URI(url)
        except InvalidURIError:
            return None
        unique_name = self.uriToUniqueName(uri)
        if unique_name is not None:
            branch = self.getByUniqueName(unique_name)
        elif uri.scheme == 'lp':
            branch = None
            allowed_hosts = set()
            for host in config.codehosting.lp_url_hosts.split(','):
                if host == '':
                    host = None
                allowed_hosts.add(host)
            if uri.host in allowed_hosts:
                try:
                    branch = self.getByLPPath(uri.path.lstrip('/'))[0]
                except NoSuchBranch:
                    pass
        else:
            branch = Branch.selectOneBy(url=url)
        if branch is None:
            return default
        else:
            return branch

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
        from canonical.launchpad.database import Person
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
        from canonical.launchpad.database import Person, Product
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
        from canonical.launchpad.database import (
            Distribution, DistroSeries, Person, SourcePackageName)
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
        segments = path.split('/')
        if len(segments) == 1:
            product_name, series_name = segments[0], None
        elif len(segments) == 2:
            product_name, series_name = tuple(segments)
        else:
            raise InvalidBranchIdentifier(path)
        if not valid_name(product_name):
            raise InvalidProductName(product_name)
        product = getUtility(IProductSet).getByName(product_name)
        if product is None:
            raise NoSuchProduct(product_name)
        if series_name is None:
            series = product.development_focus
        else:
            series = product.getSeries(series_name)
            if series is None:
                raise NoSuchProductSeries(series_name, product)
        branch = series.series_branch
        if branch is None:
            raise NoBranchForSeries(series)
        return branch, series
