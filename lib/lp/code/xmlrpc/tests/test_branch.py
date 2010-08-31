# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for the public codehosting API."""

__metaclass__ = type
__all__ = []


import os
import unittest
import xmlrpclib

from bzrlib import urlutils
from lazr.uri import URI
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad.ftests import (
    login,
    logout,
    )
from canonical.launchpad.xmlrpc import faults
from canonical.testing import DatabaseFunctionalLayer
from lp.code.enums import BranchType
from lp.code.xmlrpc.branch import PublicCodehostingAPI
from lp.services.xmlrpc import LaunchpadFault
from lp.testing import TestCaseWithFactory


NON_ASCII_NAME = u'nam\N{LATIN SMALL LETTER E WITH ACUTE}'


class TestExpandURL(TestCaseWithFactory):
    """Test the way that URLs are expanded."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        """Set up the fixture for these unit tests.

        - 'project' is an arbitrary Launchpad project.
        - 'trunk' is a branch on 'project', associated with the development
          focus.
        """
        TestCaseWithFactory.setUp(self)
        self.api = PublicCodehostingAPI(None, None)
        self.product = self.factory.makeProduct()
        # Associate 'trunk' with the product's development focus. Use
        # removeSecurityProxy so that we can assign directly to branch.
        trunk_series = removeSecurityProxy(self.product).development_focus
        # BranchType is only signficiant insofar as it is not a REMOTE branch.
        trunk_series.branch = (
            self.factory.makeProductBranch(
                branch_type=BranchType.HOSTED, product=self.product))

    def makePrivateBranch(self, **kwargs):
        """Create an arbitrary private branch using `makeBranch`."""
        branch = self.factory.makeAnyBranch(**kwargs)
        naked_branch = removeSecurityProxy(branch)
        naked_branch.private = True
        return branch

    def assertResolves(self, lp_url_path, public_branch_path,
                       ssh_branch_path=None):
        """Assert that `lp_url_path` path expands to `unique_name`.

        :param public_branch_path: The path that is accessible over http.
        :param ssh_branch_path: The path that is accessible over sftp or
            bzr+ssh.
        """
        results = self.api.resolve_lp_path(lp_url_path)
        if ssh_branch_path is None:
            ssh_branch_path = public_branch_path
        # This improves the error message if results happens to be a fault.
        if isinstance(results, LaunchpadFault):
            raise results
        for url in results['urls']:
            uri = URI(url)
            if uri.scheme == 'http':
                self.assertEqual('/' + public_branch_path, uri.path)
            else:
                self.assertEqual('/' + ssh_branch_path, uri.path)

    def assertFault(self, lp_url_path, expected_fault):
        """Trying to resolve lp_url_path raises the expected fault."""
        fault = self.api.resolve_lp_path(lp_url_path)
        self.assertTrue(
            isinstance(fault, xmlrpclib.Fault),
            "resolve_lp_path(%r) returned %r, not a Fault."
            % (lp_url_path, fault))
        self.assertEqual(expected_fault.__class__, fault.__class__)
        self.assertEqual(expected_fault.faultString, fault.faultString)
        return fault

    def test_resultDict(self):
        # A given lp url path maps to a single branch available from a number
        # of URLs (mostly varying by scheme). resolve_lp_path returns a dict
        # containing a list of these URLs, with the faster and more featureful
        # URLs earlier in the list. We use a dict so we can easily add more
        # information in the future.
        trunk = self.product.development_focus.branch
        results = self.api.resolve_lp_path(self.product.name)
        urls = [
            'bzr+ssh://bazaar.launchpad.dev/%s' % trunk.unique_name,
            'http://bazaar.launchpad.dev/%s' % trunk.unique_name]
        self.assertEqual(dict(urls=urls), results)

    def test_resultDictForHotProduct(self):
        # If 'project-name' is in the config.codehosting.hot_products list,
        # lp:project-name will only resolve to the http url.
        config.push(
            'hot_product',
            '[codehosting]\nhot_products: %s '% self.product.name)
        self.addCleanup(config.pop, 'hot_product')
        trunk = self.product.development_focus.branch
        results = self.api.resolve_lp_path(self.product.name)
        http_url = 'http://bazaar.launchpad.dev/%s' % trunk.unique_name
        self.assertEqual(dict(urls=[http_url]), results)

    def test_product_only(self):
        # lp:product expands to the branch associated with development focus
        # of the product.
        trunk = self.product.development_focus.branch
        self.assertResolves(self.product.name, trunk.unique_name)
        trunk_series = removeSecurityProxy(self.product).development_focus
        trunk_series.branch = self.factory.makeProductBranch(
            branch_type=BranchType.HOSTED, product=self.product)
        self.assertResolves(
            self.product.name, trunk_series.branch.unique_name)

    def test_product_doesnt_exist(self):
        # Return a NoSuchProduct fault if the product doesn't exist.
        self.assertFault(
            'doesntexist', faults.NoSuchProduct('doesntexist'))
        self.assertFault(
            'doesntexist/trunk', faults.NoSuchProduct('doesntexist'))

    def test_project_group(self):
        # Resolving lp:///project_group_name' should explain that project
        # groups don't have default branches.
        project_group = self.factory.makeProject()
        fault = self.assertFault(
            project_group.name, faults.CannotHaveLinkedBranch(project_group))
        self.assertIn('project group', fault.faultString)

    def test_distro_name(self):
        # Resolving lp:///distro_name' should explain that distributions don't
        # have default branches.
        distro = self.factory.makeDistribution()
        self.assertFault(distro.name, faults.CannotHaveLinkedBranch(distro))

    def test_distroseries_name(self):
        # Resolving lp:///distro/series' should explain that distribution
        # series don't have default branches.
        series = self.factory.makeDistroSeries()
        self.assertFault(
            '%s/%s' % (series.distribution.name, series.name),
            faults.CannotHaveLinkedBranch(series))

    def test_invalid_product_name(self):
        # If we get a string that cannot be a name for a product where we
        # expect the name of a product, we should error appropriately.
        invalid_name = '_' + self.factory.getUniqueString()
        self.assertFault(
            invalid_name,
            faults.InvalidProductIdentifier(invalid_name))

    def test_invalid_product_name_non_ascii(self):
        # lp:<non-ascii-string> returns InvalidProductIdentifier with the name
        # escaped.
        invalid_name = '_' + NON_ASCII_NAME
        self.assertFault(
            invalid_name,
            faults.InvalidProductIdentifier(urlutils.escape(invalid_name)))

    def test_product_and_series(self):
        # lp:product/series expands to the branch associated with the product
        # series 'series' on 'product'.
        series = self.factory.makeSeries(
            product=self.product,
            branch=self.factory.makeProductBranch(product=self.product))
        self.assertResolves(
            '%s/%s' % (self.product.name, series.name),
            series.branch.unique_name)

        # We can also use product/series notation to reach trunk.
        self.assertResolves(
            '%s/%s' % (self.product.name,
                       self.product.development_focus.name),
            self.product.development_focus.branch.unique_name)

    def test_development_focus_has_no_branch(self):
        # Return a NoLinkedBranch fault if the development focus has no branch
        # associated with it.
        product = self.factory.makeProduct()
        self.assertEqual(None, product.development_focus.branch)
        self.assertFault(product.name, faults.NoLinkedBranch(product))

    def test_series_has_no_branch(self):
        # Return a NoLinkedBranch fault if the series has no branch
        # associated with it.
        series = self.factory.makeSeries(branch=None)
        self.assertFault(
            '%s/%s' % (series.product.name, series.name),
            faults.NoLinkedBranch(series))

    def test_no_such_product_series(self):
        # Return a NoSuchProductSeries fault if there is no series of the
        # given name associated with the product.
        self.assertFault(
            '%s/%s' % (self.product.name, "doesntexist"),
            faults.NoSuchProductSeries("doesntexist", self.product))

    def test_no_such_product_series_non_ascii(self):
        # lp:product/<non-ascii-string> returns NoSuchProductSeries with the
        # name escaped.
        self.assertFault(
            '%s/%s' % (self.product.name, NON_ASCII_NAME),
            faults.NoSuchProductSeries(
                urlutils.escape(NON_ASCII_NAME), self.product))

    def test_no_such_distro_series(self):
        # Return a NoSuchDistroSeries fault if there is no series of the given
        # name on that distribution.
        distro = self.factory.makeDistribution()
        self.assertFault(
            '%s/doesntexist/whocares' % distro.name,
            faults.NoSuchDistroSeries("doesntexist"))

    def test_no_such_distro_series_non_ascii(self):
        # lp:distro/<non-ascii-string>/whatever returns NoSuchDistroSeries
        # with the name escaped.
        distro = self.factory.makeDistribution()
        self.assertFault(
            '%s/%s/whocares' % (distro.name, NON_ASCII_NAME),
            faults.NoSuchDistroSeries(urlutils.escape(NON_ASCII_NAME)))

    def test_no_such_source_package(self):
        # Return a NoSuchSourcePackageName fault if there is no source package
        # of the given name.
        distroseries = self.factory.makeDistroRelease()
        distribution = distroseries.distribution
        self.assertFault(
            '%s/%s/doesntexist' % (distribution.name, distroseries.name),
            faults.NoSuchSourcePackageName('doesntexist'))

    def test_no_such_source_package_non_ascii(self):
        # lp:distro/series/<non-ascii-name> returns NoSuchSourcePackageName
        # with the name escaped.
        distroseries = self.factory.makeDistroRelease()
        distribution = distroseries.distribution
        self.assertFault(
            '%s/%s/%s' % (
                distribution.name, distroseries.name, NON_ASCII_NAME),
            faults.NoSuchSourcePackageName(urlutils.escape(NON_ASCII_NAME)))

    def test_no_linked_branch_for_source_package(self):
        # Return a NoLinkedBranch fault if there's no linked branch for the
        # sourcepackage.
        suite_sourcepackage = self.factory.makeSuiteSourcePackage()
        self.assertFault(
            suite_sourcepackage.path,
            faults.NoLinkedBranch(suite_sourcepackage))

    def test_branch(self):
        # The unique name of a branch resolves to the unique name of the
        # branch.
        arbitrary_branch = self.factory.makeAnyBranch()
        self.assertResolves(
            arbitrary_branch.unique_name, arbitrary_branch.unique_name)
        trunk = self.product.development_focus.branch
        self.assertResolves(trunk.unique_name, trunk.unique_name)

    def test_mirrored_branch(self):
        # The unique name of a mirrored branch resolves to the unique name of
        # the branch.
        arbitrary_branch = self.factory.makeAnyBranch(
            branch_type=BranchType.MIRRORED)
        self.assertResolves(
            arbitrary_branch.unique_name, arbitrary_branch.unique_name)

    def test_no_such_branch_product(self):
        # Resolve paths to branches even if there is no branch of that name.
        # We do this so that users can push new branches to lp: URLs.
        owner = self.factory.makePerson()
        nonexistent_branch = '~%s/%s/doesntexist' % (
            owner.name, self.product.name)
        self.assertResolves(nonexistent_branch, nonexistent_branch)

    def test_no_such_branch_product_non_ascii(self):
        # A path to a branch that contains non ascii characters will never
        # find a branch, but it still resolves rather than erroring.
        owner = self.factory.makePerson()
        nonexistent_branch = u'~%s/%s/%s' % (
            owner.name, self.product.name, NON_ASCII_NAME)
        self.assertResolves(
            nonexistent_branch, urlutils.escape(nonexistent_branch))

    def test_no_such_branch_personal(self):
        # Resolve paths to junk branches.
        # This test added to make sure we don't raise a fault when looking for
        # the '+junk' project, which doesn't actually exist.
        owner = self.factory.makePerson()
        nonexistent_branch = '~%s/+junk/doesntexist' % owner.name
        self.assertResolves(
            nonexistent_branch, urlutils.escape(nonexistent_branch))

    def test_no_such_branch_package(self):
        # Resolve paths to package branches even if there's no branch of that
        # name, so that we can push new branches using lp: URLs.
        owner = self.factory.makePerson()
        sourcepackage = self.factory.makeSourcePackage()
        nonexistent_branch = '~%s/%s/doesntexist' % (
            owner.name, sourcepackage.path)
        self.assertResolves(nonexistent_branch, nonexistent_branch)

    def test_resolve_branch_with_no_such_product(self):
        # If we try to resolve a branch that refers to a non-existent product,
        # then we return a NoSuchProduct fault.
        owner = self.factory.makePerson()
        nonexistent_product_branch = "~%s/doesntexist/%s" % (
            owner.name, self.factory.getUniqueString())
        self.assertFault(
            nonexistent_product_branch, faults.NoSuchProduct('doesntexist'))

    def test_resolve_branch_with_no_such_owner(self):
        # If we try to resolve a branch that refers to a non-existent owner,
        # then we return a NoSuchPerson fault.
        nonexistent_owner_branch = "~doesntexist/%s/%s" % (
            self.factory.getUniqueString(), self.factory.getUniqueString())
        self.assertFault(
            nonexistent_owner_branch,
            faults.NoSuchPersonWithName('doesntexist'))

    def test_resolve_branch_with_no_such_owner_non_ascii(self):
        # lp:~<non-ascii-string>/product/name returns NoSuchPersonWithName
        # with the name escaped.
        nonexistent_owner_branch = u"~%s/%s/%s" % (
            NON_ASCII_NAME, self.factory.getUniqueString(),
            self.factory.getUniqueString())
        self.assertFault(
            nonexistent_owner_branch,
            faults.NoSuchPersonWithName(urlutils.escape(NON_ASCII_NAME)))

    def test_too_many_segments(self):
        # If we have more segments than are necessary to refer to a branch,
        # then attach these segments to the resolved url.
        # We do this so that users can do operations like 'bzr cat
        # lp:path/to/branch/README.txt'.
        arbitrary_branch = self.factory.makeAnyBranch()
        longer_path = os.path.join(arbitrary_branch.unique_name, 'qux')
        self.assertResolves(longer_path, longer_path)

    def test_too_many_segments_no_such_branch(self):
        # If we have more segments than are necessary to refer to a branch,
        # then attach these segments to the resolved url, even if there is no
        # branch corresponding to the start of the URL.
        # This means the users will probably get a normal Bazaar 'no such
        # branch' error when they try a command like 'bzr cat
        # lp:path/to/branch/README.txt', which probably is the least
        # surprising thing that we can do.
        person = self.factory.makePerson()
        product = self.factory.makeProduct()
        branch_name = self.factory.getUniqueString()
        extra_path = self.factory.getUniqueString()
        longer_path = os.path.join(
            '~' + person.name, product.name, branch_name, extra_path)
        self.assertResolves(longer_path, longer_path)

    def test_empty_path(self):
        # An empty path is an invalid identifier.
        self.assertFault('', faults.InvalidBranchIdentifier(''))

    def test_too_short(self):
        # Return a nice fault if the unique name is too short.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct()
        path = '%s/%s' % (owner.name, product.name)
        self.assertFault('~' + path, faults.InvalidBranchUniqueName(path))

    def test_all_slashes(self):
        # A path of all slashes is an invalid identifier.
        self.assertFault('///', faults.InvalidBranchIdentifier('///'))

    def test_trailing_slashes(self):
        # Trailing slashes are trimmed.
        # Trailing slashes on lp:product//
        trunk = self.product.development_focus.branch
        self.assertResolves(self.product.name + '/', trunk.unique_name)
        self.assertResolves(self.product.name + '//', trunk.unique_name)

        # Trailing slashes on lp:~owner/product/branch//
        arbitrary_branch = self.factory.makeAnyBranch()
        self.assertResolves(
            arbitrary_branch.unique_name + '/', arbitrary_branch.unique_name)
        self.assertResolves(
            arbitrary_branch.unique_name + '//', arbitrary_branch.unique_name)

    def test_private_branch(self):
        # Invisible branches are resolved as if they didn't exist, so that we
        # reveal the least possile amount of information about them.
        # For fully specified branch names, this means resolving the lp url.
        arbitrary_branch = self.makePrivateBranch()
        # Removing security proxy to get at the unique_name attribute of a
        # private branch, and tests are currently running as an anonymous
        # user.
        unique_name = removeSecurityProxy(arbitrary_branch).unique_name
        self.assertResolves(unique_name, unique_name)

    def test_private_branch_on_series(self):
        # We resolve invisible branches as if they don't exist.  For
        # references to product series, this means returning a
        # NoLinkedBranch fault.
        #
        # Removing security proxy because we need to be able to get at
        # attributes of a private branch and these tests are running as an
        # anonymous user.
        branch = removeSecurityProxy(self.makePrivateBranch())
        series = self.factory.makeSeries(branch=branch)
        self.assertFault(
            '%s/%s' % (series.product.name, series.name),
            faults.NoLinkedBranch(series))

    def test_private_branch_as_development_focus(self):
        # We resolve invisible branches as if they don't exist.
        #
        # References to a product resolve to the branch associated with the
        # development focus. If that branch is private, other views will
        # indicate that there is no branch on the development focus. We do the
        # same.
        trunk = self.product.development_focus.branch
        naked_trunk = removeSecurityProxy(trunk)
        naked_trunk.private = True
        self.assertFault(
            self.product.name, faults.NoLinkedBranch(self.product))

    def test_private_branch_as_user(self):
        # We resolve invisible branches as if they don't exist.
        #
        # References to a product resolve to the branch associated with the
        # development focus. If that branch is private, other views will
        # indicate that there is no branch on the development focus. We do the
        # same.
        #
        # Create the owner explicitly so that we can get its email without
        # resorting to removeSecurityProxy.
        email = self.factory.getUniqueEmailAddress()
        arbitrary_branch = self.makePrivateBranch(
            owner=self.factory.makePerson(email=email))
        login(email)
        self.addCleanup(logout)
        self.assertResolves(
            arbitrary_branch.unique_name, arbitrary_branch.unique_name)

    def test_remote_branch(self):
        # For remote branches, return results that link to the actual remote
        # branch URL.
        branch = self.factory.makeAnyBranch(branch_type=BranchType.REMOTE)
        result = self.api.resolve_lp_path(branch.unique_name)
        self.assertEqual([branch.url], result['urls'])

    def test_remote_branch_no_url(self):
        # Raise a Fault for remote branches with no URL.
        branch = self.factory.makeAnyBranch(
            branch_type=BranchType.REMOTE, url=None)
        self.assertFault(
            branch.unique_name,
            faults.NoUrlForBranch(branch.unique_name))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
