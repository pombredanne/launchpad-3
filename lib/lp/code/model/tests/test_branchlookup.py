# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the IBranchLookup implementation."""

__metaclass__ = type

from lazr.uri import URI
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.code.errors import (
    CannotHaveLinkedBranch,
    InvalidNamespace,
    NoLinkedBranch,
    NoSuchBranch,
    )
from lp.code.interfaces.branchlookup import (
    IBranchLookup,
    ILinkedBranchTraverser,
    )
from lp.code.interfaces.branchnamespace import get_branch_namespace
from lp.code.interfaces.codehosting import (
    branch_id_alias,
    BRANCH_ID_ALIAS_PREFIX,
    )
from lp.code.interfaces.linkedbranch import ICanHasLinkedBranch
from lp.registry.errors import (
    NoSuchDistroSeries,
    NoSuchSourcePackageName,
    )
from lp.registry.interfaces.person import NoSuchPerson
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.product import (
    InvalidProductName,
    NoSuchProduct,
    )
from lp.registry.interfaces.productseries import NoSuchProductSeries
from lp.testing import (
    person_logged_in,
    run_with_login,
    TestCaseWithFactory,
    )


class TestGetByUniqueName(TestCaseWithFactory):
    """Tests for `IBranchLookup.getByUniqueName`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.branch_set = getUtility(IBranchLookup)

    def test_not_found(self):
        unused_name = self.factory.getUniqueString()
        found = self.branch_set.getByUniqueName(unused_name)
        self.assertIs(None, found)

    def test_junk(self):
        branch = self.factory.makePersonalBranch()
        found_branch = self.branch_set.getByUniqueName(branch.unique_name)
        self.assertEqual(branch, found_branch)

    def test_product(self):
        branch = self.factory.makeProductBranch()
        found_branch = self.branch_set.getByUniqueName(branch.unique_name)
        self.assertEqual(branch, found_branch)

    def test_source_package(self):
        branch = self.factory.makePackageBranch()
        found_branch = self.branch_set.getByUniqueName(branch.unique_name)
        self.assertEqual(branch, found_branch)


class TestGetIdAndTrailingPath(TestCaseWithFactory):
    """Tests for `IBranchLookup.getIdAndTrailingPath`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.branch_set = getUtility(IBranchLookup)

    def test_not_found(self):
        unused_name = self.factory.getUniqueString()
        result = self.branch_set.getIdAndTrailingPath('/' + unused_name)
        self.assertEqual((None, None), result)

    def test_junk(self):
        branch = self.factory.makePersonalBranch()
        result = self.branch_set.getIdAndTrailingPath(
            '/' + branch.unique_name)
        self.assertEqual((branch.id, ''), result)

    def test_product(self):
        branch = self.factory.makeProductBranch()
        result = self.branch_set.getIdAndTrailingPath(
            '/' + branch.unique_name)
        self.assertEqual((branch.id, ''), result)

    def test_source_package(self):
        branch = self.factory.makePackageBranch()
        result = self.branch_set.getIdAndTrailingPath(
            '/' + branch.unique_name)
        self.assertEqual((branch.id, ''), result)

    def test_trailing_slash(self):
        branch = self.factory.makeAnyBranch()
        result = self.branch_set.getIdAndTrailingPath(
            '/' + branch.unique_name + '/')
        self.assertEqual((branch.id, '/'), result)

    def test_trailing_path(self):
        branch = self.factory.makeAnyBranch()
        path = self.factory.getUniqueString()
        result = self.branch_set.getIdAndTrailingPath(
            '/' + branch.unique_name + '/' + path)
        self.assertEqual((branch.id, '/' + path), result)

    def test_branch_id_alias(self):
        # The prefix by itself returns no branch, and no path.
        path = BRANCH_ID_ALIAS_PREFIX
        result = self.branch_set.getIdAndTrailingPath('/' + path)
        self.assertEqual((None, None), result)

    def test_branch_id_alias_not_int(self):
        # The prefix followed by a non-integer returns no branch and no path.
        path = BRANCH_ID_ALIAS_PREFIX + '/foo'
        result = self.branch_set.getIdAndTrailingPath('/' + path)
        self.assertEqual((None, None), result)

    def test_branch_id_alias_private(self):
        # Private branches are not found at all (this is for anonymous access)
        owner = self.factory.makePerson()
        branch = self.factory.makeAnyBranch(owner=owner, private=True)
        with person_logged_in(owner):
            path = branch_id_alias(branch)
        result = self.branch_set.getIdAndTrailingPath(path)
        self.assertEqual((None, None), result)

    def test_branch_id_alias_transitive_private(self):
        # Transitively private branches are not found at all
        # (this is for anonymous access)
        owner = self.factory.makePerson()
        private_branch = self.factory.makeAnyBranch(
            owner=owner, private=True)
        branch = self.factory.makeAnyBranch(stacked_on=private_branch)
        with person_logged_in(owner):
            path = branch_id_alias(branch)
        result = self.branch_set.getIdAndTrailingPath(path)
        self.assertEqual((None, None), result)

    def test_branch_id_alias_public(self):
        # Public branches can be accessed.
        branch = self.factory.makeAnyBranch()
        path = branch_id_alias(branch)
        result = self.branch_set.getIdAndTrailingPath(path)
        self.assertEqual((branch.id, ''), result)

    def test_branch_id_alias_public_slash(self):
        # A trailing slash is returned as the extra path.
        branch = self.factory.makeAnyBranch()
        path = '%s/' % branch_id_alias(branch)
        result = self.branch_set.getIdAndTrailingPath(path)
        self.assertEqual((branch.id, '/'), result)

    def test_branch_id_alias_public_with_path(self):
        # All the path after the number is returned as the trailing path.
        branch = self.factory.makeAnyBranch()
        path = '%s/foo' % branch_id_alias(branch)
        result = self.branch_set.getIdAndTrailingPath(path)
        self.assertEqual((branch.id, '/foo'), result)


class TestGetByPath(TestCaseWithFactory):
    """Test `IBranchLookup.getByLPPath`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.branch_lookup = getUtility(IBranchLookup)

    def getByPath(self, path):
        return self.branch_lookup.getByLPPath(path)

    def makeRelativePath(self):
        arbitrary_num_segments = 7
        return '/'.join([
            self.factory.getUniqueString()
            for i in range(arbitrary_num_segments)])

    def test_finds_exact_personal_branch(self):
        branch = self.factory.makePersonalBranch()
        found_branch, suffix = self.getByPath(branch.unique_name)
        self.assertEqual(branch, found_branch)
        self.assertEqual(None, suffix)

    def test_finds_suffixed_personal_branch(self):
        branch = self.factory.makePersonalBranch()
        suffix = self.makeRelativePath()
        found_branch, found_suffix = self.getByPath(
            branch.unique_name + '/' + suffix)
        self.assertEqual(branch, found_branch)
        self.assertEqual(suffix, found_suffix)

    def test_missing_personal_branch(self):
        owner = self.factory.makePerson()
        namespace = get_branch_namespace(owner)
        branch_name = namespace.getBranchName(self.factory.getUniqueString())
        self.assertRaises(NoSuchBranch, self.getByPath, branch_name)

    def test_missing_suffixed_personal_branch(self):
        owner = self.factory.makePerson()
        namespace = get_branch_namespace(owner)
        branch_name = namespace.getBranchName(self.factory.getUniqueString())
        suffix = self.makeRelativePath()
        self.assertRaises(
            NoSuchBranch, self.getByPath, branch_name + '/' + suffix)

    def test_finds_exact_product_branch(self):
        branch = self.factory.makeProductBranch()
        found_branch, suffix = self.getByPath(branch.unique_name)
        self.assertEqual(branch, found_branch)
        self.assertEqual(None, suffix)

    def test_finds_suffixed_product_branch(self):
        branch = self.factory.makeProductBranch()
        suffix = self.makeRelativePath()
        found_branch, found_suffix = self.getByPath(
            branch.unique_name + '/' + suffix)
        self.assertEqual(branch, found_branch)
        self.assertEqual(suffix, found_suffix)

    def test_missing_product_branch(self):
        owner = self.factory.makePerson()
        product = self.factory.makeProduct()
        namespace = get_branch_namespace(owner, product=product)
        branch_name = namespace.getBranchName(self.factory.getUniqueString())
        self.assertRaises(NoSuchBranch, self.getByPath, branch_name)

    def test_missing_suffixed_product_branch(self):
        owner = self.factory.makePerson()
        product = self.factory.makeProduct()
        namespace = get_branch_namespace(owner, product=product)
        suffix = self.makeRelativePath()
        branch_name = namespace.getBranchName(self.factory.getUniqueString())
        self.assertRaises(
            NoSuchBranch, self.getByPath, branch_name + '/' + suffix)

    def test_finds_exact_package_branch(self):
        branch = self.factory.makePackageBranch()
        found_branch, suffix = self.getByPath(branch.unique_name)
        self.assertEqual(branch, found_branch)
        self.assertEqual(None, suffix)

    def test_missing_package_branch(self):
        owner = self.factory.makePerson()
        distroseries = self.factory.makeDistroSeries()
        sourcepackagename = self.factory.makeSourcePackageName()
        namespace = get_branch_namespace(
            owner, distroseries=distroseries,
            sourcepackagename=sourcepackagename)
        branch_name = namespace.getBranchName(self.factory.getUniqueString())
        self.assertRaises(NoSuchBranch, self.getByPath, branch_name)

    def test_missing_suffixed_package_branch(self):
        owner = self.factory.makePerson()
        distroseries = self.factory.makeDistroSeries()
        sourcepackagename = self.factory.makeSourcePackageName()
        namespace = get_branch_namespace(
            owner, distroseries=distroseries,
            sourcepackagename=sourcepackagename)
        suffix = self.makeRelativePath()
        branch_name = namespace.getBranchName(self.factory.getUniqueString())
        self.assertRaises(
            NoSuchBranch, self.getByPath, branch_name + '/' + suffix)

    def test_too_short(self):
        person = self.factory.makePerson()
        self.assertRaises(
            InvalidNamespace, self.getByPath, '~%s' % person.name)

    def test_no_such_product(self):
        person = self.factory.makePerson()
        branch_name = '~%s/%s/%s' % (
            person.name, self.factory.getUniqueString(), 'branch-name')
        self.assertRaises(NoSuchProduct, self.getByPath, branch_name)


class TestGetByUrl(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def makeProductBranch(self):
        """Create a branch with aa/b/c as its unique name."""
        # XXX: JonathanLange 2009-01-13 spec=package-branches: This test is
        # bad because it assumes that the interesting branches for testing are
        # product branches.
        owner = self.factory.makePerson(name='aa')
        product = self.factory.makeProduct('b')
        return self.factory.makeProductBranch(
            owner=owner, product=product, name='c')

    def test_getByUrl_with_none(self):
        """getByUrl returns None if given None."""
        self.assertIs(None, getUtility(IBranchLookup).getByUrl(None))

    def test_getByUrl_with_trailing_slash(self):
        # Trailing slashes are stripped from the url prior to searching.
        branch = self.makeProductBranch()
        lookup = getUtility(IBranchLookup)
        branch2 = lookup.getByUrl('http://bazaar.launchpad.dev/~aa/b/c/')
        self.assertEqual(branch, branch2)

    def test_getByUrl_with_http(self):
        """getByUrl recognizes LP branches for http URLs."""
        branch = self.makeProductBranch()
        branch_set = getUtility(IBranchLookup)
        branch2 = branch_set.getByUrl('http://bazaar.launchpad.dev/~aa/b/c')
        self.assertEqual(branch, branch2)

    def test_getByUrl_with_ssh(self):
        """getByUrl recognizes LP branches for bzr+ssh URLs."""
        branch = self.makeProductBranch()
        branch_set = getUtility(IBranchLookup)
        branch2 = branch_set.getByUrl(
            'bzr+ssh://bazaar.launchpad.dev/~aa/b/c')
        self.assertEqual(branch, branch2)

    def test_getByUrl_with_sftp(self):
        """getByUrl recognizes LP branches for sftp URLs."""
        branch = self.makeProductBranch()
        branch_set = getUtility(IBranchLookup)
        branch2 = branch_set.getByUrl('sftp://bazaar.launchpad.dev/~aa/b/c')
        self.assertEqual(branch, branch2)

    def test_getByUrl_with_ftp(self):
        """getByUrl does not recognize LP branches for ftp URLs.

        This is because Launchpad doesn't currently support ftp.
        """
        self.makeProductBranch()
        branch_set = getUtility(IBranchLookup)
        branch2 = branch_set.getByUrl('ftp://bazaar.launchpad.dev/~aa/b/c')
        self.assertIs(None, branch2)

    def test_getByURL_with_lp_prefix(self):
        """lp: URLs for the configured prefix are supported."""
        branch_set = getUtility(IBranchLookup)
        url = '%s~aa/b/c' % config.codehosting.bzr_lp_prefix
        self.assertIs(None, branch_set.getByUrl(url))
        owner = self.factory.makePerson(name='aa')
        product = self.factory.makeProduct('b')
        branch2 = branch_set.getByUrl(url)
        self.assertIs(None, branch2)
        branch = self.factory.makeProductBranch(
            owner=owner, product=product, name='c')
        branch2 = branch_set.getByUrl(url)
        self.assertEqual(branch, branch2)

    def test_getByURL_for_production(self):
        """test_getByURL works with production values."""
        branch_set = getUtility(IBranchLookup)
        branch = self.makeProductBranch()
        self.pushConfig('codehosting', lp_url_hosts='production,,')
        branch2 = branch_set.getByUrl('lp://staging/~aa/b/c')
        self.assertIs(None, branch2)
        branch2 = branch_set.getByUrl('lp://asdf/~aa/b/c')
        self.assertIs(None, branch2)
        branch2 = branch_set.getByUrl('lp:~aa/b/c')
        self.assertEqual(branch, branch2)
        branch2 = branch_set.getByUrl('lp://production/~aa/b/c')
        self.assertEqual(branch, branch2)

    def test_getByUrls(self):
        # getByUrls returns a dictionary mapping branches to URLs.
        branch1 = self.factory.makeAnyBranch()
        branch2 = self.factory.makeAnyBranch()
        url3 = 'http://example.com/%s' % self.factory.getUniqueString()
        branch_set = getUtility(IBranchLookup)
        branches = branch_set.getByUrls(
            [branch1.bzr_identity, branch2.bzr_identity, url3])
        self.assertEqual(
            {branch1.bzr_identity: branch1,
             branch2.bzr_identity: branch2,
             url3: None}, branches)

    def test_uriToUniqueName(self):
        """Ensure uriToUniqueName works.

        Only codehosting-based using http, sftp or bzr+ssh URLs will
        be handled. If any other URL gets passed the returned will be
        None.
        """
        branch_set = getUtility(IBranchLookup)
        uri = URI(config.codehosting.supermirror_root)
        uri.path = '/~foo/bar/baz'
        # Test valid schemes
        uri.scheme = 'http'
        self.assertEqual('~foo/bar/baz', branch_set.uriToUniqueName(uri))
        uri.scheme = 'sftp'
        self.assertEqual('~foo/bar/baz', branch_set.uriToUniqueName(uri))
        uri.scheme = 'bzr+ssh'
        self.assertEqual('~foo/bar/baz', branch_set.uriToUniqueName(uri))
        # Test invalid scheme
        uri.scheme = 'ftp'
        self.assertIs(None, branch_set.uriToUniqueName(uri))
        # Test valid scheme, invalid domain
        uri.scheme = 'sftp'
        uri.host = 'example.com'
        self.assertIs(None, branch_set.uriToUniqueName(uri))


class TestLinkedBranchTraverser(TestCaseWithFactory):
    """Tests for the linked branch traverser."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.traverser = getUtility(ILinkedBranchTraverser)

    def assertTraverses(self, path, result):
        """Assert that 'path' resolves to 'result'."""
        self.assertEqual(result, self.traverser.traverse(path))

    def test_error_fallthrough_product_series(self):
        # For the short name of a series branch, `traverse` raises
        # `NoSuchProduct` if the first component refers to a non-existent
        # product, and `NoSuchProductSeries` if the second component refers to
        # a non-existent series.
        self.assertRaises(
            NoSuchProduct, self.traverser.traverse, 'bb/dd')
        self.factory.makeProduct(name='bb')
        self.assertRaises(
            NoSuchProductSeries, self.traverser.traverse, 'bb/dd')

    def test_product_series(self):
        # `traverse` resolves the path to a product series to the product
        # series itself.
        series = self.factory.makeProductSeries()
        short_name = '%s/%s' % (series.product.name, series.name)
        self.assertTraverses(short_name, series)

    def test_product_that_doesnt_exist(self):
        # `traverse` raises `NoSuchProduct` when resolving an lp path of
        # 'product' if the product doesn't exist.
        self.assertRaises(NoSuchProduct, self.traverser.traverse, 'bb')

    def test_invalid_product(self):
        # `traverse` raises `InvalidProductIdentifier` when resolving an lp
        # path for a completely invalid product development focus branch.
        self.assertRaises(
            InvalidProductName, self.traverser.traverse, 'b')

    def test_product(self):
        # `traverse` resolves the name of a product to the product itself.
        product = self.factory.makeProduct()
        self.assertTraverses(product.name, product)

    def test_source_package(self):
        # `traverse` resolves 'distro/series/package' to the release pocket of
        # that package in that series.
        package = self.factory.makeSourcePackage()
        ssp = package.getSuiteSourcePackage(PackagePublishingPocket.RELEASE)
        self.assertTraverses(package.path, ssp)

    def test_distribution_source_package(self):
        # `traverse` resolves 'distro/package' to the distribution source
        # package.
        dsp = self.factory.makeDistributionSourcePackage()
        path = '%s/%s' % (dsp.distribution.name, dsp.sourcepackagename.name)
        self.assertTraverses(path, dsp)

    def test_traverse_source_package_pocket(self):
        # `traverse` resolves 'distro/series-pocket/package' to the official
        # branch for 'pocket' on that package.
        package = self.factory.makeSourcePackage()
        pocket = PackagePublishingPocket.BACKPORTS
        ssp = package.getSuiteSourcePackage(pocket)
        package = self.factory.makeSourcePackage()
        self.assertTraverses(ssp.path, ssp)

    def test_no_such_distribution(self):
        # `traverse` raises `NoSuchProduct` error if the distribution doesn't
        # exist. That's because it can't tell the difference between the name
        # of a product that doesn't exist and the name of a distribution that
        # doesn't exist.
        self.assertRaises(
            NoSuchProduct, self.traverser.traverse,
            'distro/series/package')

    def test_no_such_distro_series(self):
        # `traverse` raises `NoSuchDistroSeries` if the distro series doesn't
        # exist.
        self.factory.makeDistribution(name='distro')
        self.assertRaises(
            NoSuchDistroSeries, self.traverser.traverse,
            'distro/series/package')

    def test_no_such_sourcepackagename(self):
        # `traverse` raises `NoSuchSourcePackageName` if the package in
        # distro/series/package doesn't exist.
        distroseries = self.factory.makeDistroSeries()
        path = '%s/%s/doesntexist' % (
            distroseries.distribution.name, distroseries.name)
        self.assertRaises(
            NoSuchSourcePackageName, self.traverser.traverse, path)

    def test_no_such_distribution_sourcepackage(self):
        # `traverse` raises `NoSuchSourcePackageName` if the package in
        # distro/package doesn't exist.
        distribution = self.factory.makeDistribution()
        path = '%s/doesntexist' % distribution.name
        self.assertRaises(
            NoSuchSourcePackageName, self.traverser.traverse, path)


class TestGetByLPPath(TestCaseWithFactory):
    """Ensure URLs are correctly expanded."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.branch_lookup = getUtility(IBranchLookup)

    def test_error_fallthrough_product_branch(self):
        # getByLPPath raises `NoSuchPerson` if the person component is not
        # found, then `NoSuchProduct` if the person component is found but the
        # product component isn't, then `NoSuchBranch` if the first two
        # components are found.
        self.assertRaises(
            NoSuchPerson, self.branch_lookup.getByLPPath, '~aa/bb/c')
        self.factory.makePerson(name='aa')
        self.assertRaises(
            NoSuchProduct, self.branch_lookup.getByLPPath, '~aa/bb/c')
        self.factory.makeProduct(name='bb')
        self.assertRaises(
            NoSuchBranch, self.branch_lookup.getByLPPath, '~aa/bb/c')

    def test_private_branch(self):
        # If the unique name refers to an invisible branch, getByLPPath raises
        # NoSuchBranch, just as if the branch weren't there at all.
        branch = self.factory.makeAnyBranch(private=True)
        path = removeSecurityProxy(branch).unique_name
        self.assertRaises(
            NoSuchBranch, self.branch_lookup.getByLPPath, path)

    def test_transitive_private_branch(self):
        # If the unique name refers to an invisible branch, getByLPPath raises
        # NoSuchBranch, just as if the branch weren't there at all.
        private_branch = self.factory.makeAnyBranch(private=True)
        branch = self.factory.makeAnyBranch(stacked_on=private_branch)
        path = removeSecurityProxy(branch).unique_name
        self.assertRaises(
            NoSuchBranch, self.branch_lookup.getByLPPath, path)

    def test_resolve_product_branch_unique_name(self):
        # getByLPPath returns the branch, no trailing path and no series if
        # given the unique name of an existing product branch.
        branch = self.factory.makeProductBranch()
        self.assertEqual(
            (branch, None),
            self.branch_lookup.getByLPPath(branch.unique_name))

    def test_resolve_product_branch_unique_name_with_trailing(self):
        # getByLPPath returns the branch and the trailing path (with no
        # series) if the given path is inside an existing branch.
        branch = self.factory.makeProductBranch()
        path = '%s/foo/bar/baz' % (branch.unique_name)
        self.assertEqual(
            (branch, 'foo/bar/baz'), self.branch_lookup.getByLPPath(path))

    def test_error_fallthrough_personal_branch(self):
        # getByLPPath raises `NoSuchPerson` if the first component doesn't
        # match an existing person, and `NoSuchBranch` if the last component
        # doesn't match an existing branch.
        self.assertRaises(
            NoSuchPerson, self.branch_lookup.getByLPPath, '~aa/+junk/c')
        self.factory.makePerson(name='aa')
        self.assertRaises(
            NoSuchBranch, self.branch_lookup.getByLPPath, '~aa/+junk/c')

    def test_resolve_personal_branch_unique_name(self):
        # getByLPPath returns the branch, no trailing path and no series if
        # given the unique name of an existing junk branch.
        branch = self.factory.makePersonalBranch()
        self.assertEqual(
            (branch, None),
            self.branch_lookup.getByLPPath(branch.unique_name))

    def test_resolve_personal_branch_unique_name_with_trailing(self):
        # getByLPPath returns the branch and the trailing path (with no
        # series) if the given path is inside an existing branch.
        branch = self.factory.makePersonalBranch()
        path = '%s/foo/bar/baz' % (branch.unique_name)
        self.assertEqual(
            (branch, 'foo/bar/baz'),
            self.branch_lookup.getByLPPath(path))

    def test_resolve_distro_package_branch(self):
        # getByLPPath returns the branch associated with the distribution
        # source package referred to by the path.
        sourcepackage = self.factory.makeSourcePackage()
        branch = self.factory.makePackageBranch(sourcepackage=sourcepackage)
        distro_package = sourcepackage.distribution_sourcepackage
        registrant = sourcepackage.distribution.owner
        run_with_login(
            registrant,
            ICanHasLinkedBranch(distro_package).setBranch, branch, registrant)
        self.assertEqual(
            (branch, None),
            self.branch_lookup.getByLPPath(
                '%s/%s' % (
                    distro_package.distribution.name,
                    distro_package.sourcepackagename.name)))

    def test_no_product_series_branch(self):
        # getByLPPath raises `NoLinkedBranch` if there's no branch registered
        # linked to the requested series.
        series = self.factory.makeProductSeries()
        short_name = '%s/%s' % (series.product.name, series.name)
        exception = self.assertRaises(
            NoLinkedBranch, self.branch_lookup.getByLPPath, short_name)
        self.assertEqual(series, exception.component)

    def test_product_with_no_dev_focus(self):
        # getByLPPath raises `NoLinkedBranch` if the product is found but
        # doesn't have a development focus branch.
        product = self.factory.makeProduct()
        exception = self.assertRaises(
            NoLinkedBranch, self.branch_lookup.getByLPPath, product.name)
        self.assertEqual(product, exception.component)

    def test_private_linked_branch(self):
        # If the given path refers to an object with an invisible linked
        # branch, then getByLPPath raises `NoLinkedBranch`, as if the branch
        # weren't there at all.
        branch = self.factory.makeProductBranch(private=True)
        product = removeSecurityProxy(branch).product
        removeSecurityProxy(product).development_focus.branch = branch
        self.assertRaises(
            NoLinkedBranch, self.branch_lookup.getByLPPath, product.name)

    def test_transitive_private_linked_branch(self):
        # If the given path refers to an object with an invisible linked
        # branch, then getByLPPath raises `NoLinkedBranch`, as if the branch
        # weren't there at all.
        private_branch = self.factory.makeProductBranch(private=True)
        branch = self.factory.makeProductBranch(stacked_on=private_branch)
        product = removeSecurityProxy(branch).product
        removeSecurityProxy(product).development_focus.branch = branch
        self.assertRaises(
            NoLinkedBranch, self.branch_lookup.getByLPPath, product.name)

    def test_no_official_branch(self):
        sourcepackage = self.factory.makeSourcePackage()
        exception = self.assertRaises(
            NoLinkedBranch,
            self.branch_lookup.getByLPPath, sourcepackage.path)
        suite_sourcepackage = sourcepackage.getSuiteSourcePackage(
            PackagePublishingPocket.RELEASE)
        self.assertEqual(suite_sourcepackage, exception.component)

    def test_distribution_linked_branch(self):
        # Distributions cannot have linked branches, so `getByLPPath` raises a
        # `CannotHaveLinkedBranch` error if we try to get the linked branch
        # for a distribution.
        distribution = self.factory.makeDistribution()
        exception = self.assertRaises(
            CannotHaveLinkedBranch,
            self.branch_lookup.getByLPPath, distribution.name)
        self.assertEqual(distribution, exception.component)

    def test_distribution_with_no_series(self):
        distro_package = self.factory.makeDistributionSourcePackage()
        path = ICanHasLinkedBranch(distro_package).bzr_path
        self.assertRaises(
            NoLinkedBranch, self.branch_lookup.getByLPPath, path)

    def test_project_linked_branch(self):
        # ProjectGroups cannot have linked branches, so `getByLPPath` raises a
        # `CannotHaveLinkedBranch` error if we try to get the linked branch
        # for a project.
        project = self.factory.makeProject()
        exception = self.assertRaises(
            CannotHaveLinkedBranch,
            self.branch_lookup.getByLPPath, project.name)
        self.assertEqual(project, exception.component)

    def test_partial_lookup(self):
        owner = self.factory.makePerson()
        product = self.factory.makeProduct()
        path = '~%s/%s' % (owner.name, product.name)
        self.assertRaises(
            InvalidNamespace, self.branch_lookup.getByLPPath, path)

    def test_too_long_product(self):
        # If the provided path points to an existing product with a linked
        # branch but there are also extra path segments, then raise a
        # NoSuchProductSeries error, since we can't tell the difference
        # between a trailing path and an attempt to load a non-existent series
        # branch.
        branch = self.factory.makeProductBranch()
        product = removeSecurityProxy(branch.product)
        product.development_focus.branch = branch
        self.assertRaises(
            NoSuchProductSeries,
            self.branch_lookup.getByLPPath, '%s/other/bits' % product.name)

    def test_too_long_product_series(self):
        # If the provided path points to an existing product series with a
        # linked branch but is followed by extra path segments, then we return
        # the linked branch but chop off the extra segments. We might want to
        # change this behaviour in future.
        branch = self.factory.makeBranch()
        series = self.factory.makeProductSeries(branch=branch)
        result = self.branch_lookup.getByLPPath(
            '%s/%s/other/bits' % (series.product.name, series.name))
        self.assertEqual((branch, u'other/bits'), result)

    def test_too_long_sourcepackage(self):
        # If the provided path points to an existing source package with a
        # linked branch but is followed by extra path segments, then we return
        # the linked branch but chop off the extra segments. We might want to
        # change this behaviour in future.
        package = self.factory.makeSourcePackage()
        branch = self.factory.makePackageBranch(sourcepackage=package)
        with person_logged_in(package.distribution.owner):
            package.setBranch(
                PackagePublishingPocket.RELEASE, branch,
                package.distribution.owner)
        result = self.branch_lookup.getByLPPath(
            '%s/other/bits' % package.path)
        self.assertEqual((branch, u'other/bits'), result)
