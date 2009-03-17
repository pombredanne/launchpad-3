# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for `IBranchNamespace` implementations."""

__metaclass__ = type

import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.database.branchnamespace import (
    PackageNamespace, PersonalNamespace, ProductNamespace)
from canonical.launchpad.database.sourcepackage import SourcePackage
from canonical.launchpad.interfaces.branch import (
    BranchLifecycleStatus, BranchType, NoSuchBranch)
from canonical.launchpad.interfaces.branchnamespace import (
    get_branch_namespace, IBranchNamespace, IBranchNamespaceSet,
    lookup_branch_namespace, InvalidNamespace)
from canonical.launchpad.interfaces.branchvisibilitypolicy import (
    BranchVisibilityRule)
from canonical.launchpad.interfaces.distribution import NoSuchDistribution
from canonical.launchpad.interfaces.distroseries import NoSuchDistroSeries
from canonical.launchpad.interfaces.person import NoSuchPerson
from canonical.launchpad.interfaces.product import NoSuchProduct
from canonical.launchpad.interfaces.sourcepackagename import (
    NoSuchSourcePackageName)
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.testing import DatabaseFunctionalLayer


class NamespaceMixin:
    """Tests common to all namespace implementations.

    You might even call these 'interface tests'.
    """

    def test_provides_interface(self):
        # All branch namespaces provide IBranchNamespace.
        self.assertProvides(self.getNamespace(), IBranchNamespace)

    def test_getBranchName(self):
        # getBranchName returns the thing that would be the
        # IBranch.unique_name of a branch with that name in the namespace.
        namespace = self.getNamespace()
        branch_name = self.factory.getUniqueString()
        self.assertEqual(
            '%s/%s' % (namespace.name, branch_name),
            namespace.getBranchName(branch_name))

    def test_createBranch_right_namespace(self):
        # createBranch creates a branch in that namespace.
        namespace = self.getNamespace()
        branch_name = self.factory.getUniqueString()
        expected_unique_name = namespace.getBranchName(branch_name)
        registrant = removeSecurityProxy(namespace).owner
        branch = namespace.createBranch(
            BranchType.HOSTED, branch_name, registrant)
        self.assertEqual(
            expected_unique_name, branch.unique_name)

    def test_createBranch_passes_through(self):
        # createBranch takes all the arguments that IBranchSet.new takes,
        # except for the ones that define the namespace.
        namespace = self.getNamespace()
        branch_name = self.factory.getUniqueString()
        registrant = removeSecurityProxy(namespace).owner
        title = self.factory.getUniqueString()
        summary = self.factory.getUniqueString()
        whiteboard = self.factory.getUniqueString()
        branch = namespace.createBranch(
            BranchType.HOSTED, branch_name, registrant, url=None,
            title=title, lifecycle_status=BranchLifecycleStatus.EXPERIMENTAL,
            summary=summary, whiteboard=whiteboard)
        self.assertEqual(BranchType.HOSTED, branch.branch_type)
        self.assertEqual(branch_name, branch.name)
        self.assertEqual(registrant, branch.registrant)
        self.assertIs(None, branch.url)
        self.assertEqual(title, branch.title)
        self.assertEqual(
            BranchLifecycleStatus.EXPERIMENTAL, branch.lifecycle_status)
        self.assertEqual(summary, branch.summary)
        self.assertEqual(whiteboard, branch.whiteboard)

    def test_getBranches_no_branches(self):
        # getBranches on an IBranchNamespace returns a result set of branches
        # in that namespace. If there are no branches, the result set is
        # empty.
        namespace = self.getNamespace()
        self.assertEqual([], list(namespace.getBranches()))

    def test_getBranches_some_branches(self):
        # getBranches on an IBranchNamespace returns a result set of branches
        # in that namespace.
        namespace = self.getNamespace()
        branch_name = self.factory.getUniqueString()
        branch = namespace.createBranch(
            BranchType.HOSTED, branch_name,
            removeSecurityProxy(namespace).owner)
        self.assertEqual([branch], list(namespace.getBranches()))

    def test_getByName_default(self):
        # getByName returns the given default if there is no branch in the
        # namespace with that name.
        namespace = self.getNamespace()
        default = object()
        match = namespace.getByName(self.factory.getUniqueString(), default)
        self.assertIs(default, match)

    def test_getByName_default_is_none(self):
        # The default 'default' return value is None.
        namespace = self.getNamespace()
        match = namespace.getByName(self.factory.getUniqueString())
        self.assertIs(None, match)

    def test_getByName_matches(self):
        namespace = self.getNamespace()
        branch_name = self.factory.getUniqueString()
        branch = namespace.createBranch(
            BranchType.HOSTED, branch_name,
            removeSecurityProxy(namespace).owner)
        match = namespace.getByName(branch_name)
        self.assertEqual(branch, match)

    def test_isNameUsed_not(self):
        namespace = self.getNamespace()
        name = self.factory.getUniqueString()
        self.assertEqual(False, namespace.isNameUsed(name))

    def test_isNameUsed_yes(self):
        namespace = self.getNamespace()
        branch_name = self.factory.getUniqueString()
        branch = namespace.createBranch(
            BranchType.HOSTED, branch_name,
            removeSecurityProxy(namespace).owner)
        self.assertEqual(True, namespace.isNameUsed(branch_name))

    def test_findUnusedName_unused(self):
        # findUnusedName returns the given name if that name is not used.
        namespace = self.getNamespace()
        name = self.factory.getUniqueString()
        unused_name = namespace.findUnusedName(name)
        self.assertEqual(name, unused_name)

    def test_findUnusedName_used(self):
        # findUnusedName returns the given name with a numeric suffix if its
        # already used.
        namespace = self.getNamespace()
        name = self.factory.getUniqueString()
        namespace.createBranch(
            BranchType.HOSTED, name, removeSecurityProxy(namespace).owner)
        unused_name = namespace.findUnusedName(name)
        self.assertEqual('%s-1' % name, unused_name)

    def test_findUnusedName_used_twice(self):
        # findUnusedName returns the given name with a numeric suffix if its
        # already used.
        namespace = self.getNamespace()
        name = self.factory.getUniqueString()
        namespace.createBranch(
            BranchType.HOSTED, name, removeSecurityProxy(namespace).owner)
        namespace.createBranch(
            BranchType.HOSTED, name + '-1',
            removeSecurityProxy(namespace).owner)
        unused_name = namespace.findUnusedName(name)
        self.assertEqual('%s-2' % name, unused_name)

    def test_createBranchWithPrefix_unused(self):
        # createBranch with prefix creates a branch with the same name as the
        # given prefix if there's no branch with that name already.
        namespace = self.getNamespace()
        name = self.factory.getUniqueString()
        branch = namespace.createBranchWithPrefix(
            BranchType.HOSTED, name, removeSecurityProxy(namespace).owner)
        self.assertEqual(name, branch.name)

    def test_createBranchWithPrefix_used(self):
        # createBranch with prefix creates a branch with the same name as the
        # given prefix if there's no branch with that name already.
        namespace = self.getNamespace()
        name = self.factory.getUniqueString()
        namespace.createBranch(
            BranchType.HOSTED, name, removeSecurityProxy(namespace).owner)
        branch = namespace.createBranchWithPrefix(
            BranchType.HOSTED, name, removeSecurityProxy(namespace).owner)
        self.assertEqual(name + '-1', branch.name)


class TestPersonalNamespace(TestCaseWithFactory, NamespaceMixin):
    """Tests for `PersonalNamespace`."""

    layer = DatabaseFunctionalLayer

    def getNamespace(self):
        return get_branch_namespace(person=self.factory.makePerson())

    def test_name(self):
        # A personal namespace has branches with names starting with
        # ~foo/+junk.
        person = self.factory.makePerson()
        namespace = PersonalNamespace(person)
        self.assertEqual('~%s/+junk' % person.name, namespace.name)

    def test_owner(self):
        # The person passed to a personal namespace is the owner.
        person = self.factory.makePerson()
        namespace = PersonalNamespace(person)
        self.assertEqual(person, removeSecurityProxy(namespace).owner)


class TestPersonalNamespacePrivacy(TestCaseWithFactory):
    """Tests for the privacy aspects of `PersonalNamespace`."""

    layer = DatabaseFunctionalLayer

    def test_subscriber(self):
        # There are no implicit subscribers for a personal namespace.
        person = self.factory.makePerson()
        namespace = PersonalNamespace(person)
        self.assertIs(None, namespace.getPrivacySubscriber())


class TestProductNamespace(TestCaseWithFactory, NamespaceMixin):
    """Tests for `ProductNamespace`."""

    layer = DatabaseFunctionalLayer

    def getNamespace(self):
        return get_branch_namespace(
            person=self.factory.makePerson(),
            product=self.factory.makeProduct())

    def test_name(self):
        # A product namespace has branches with names starting with ~foo/bar.
        person = self.factory.makePerson()
        product = self.factory.makeProduct()
        namespace = ProductNamespace(person, product)
        self.assertEqual(
            '~%s/%s' % (person.name, product.name), namespace.name)

    def test_owner(self):
        # The person passed to a product namespace is the owner.
        person = self.factory.makePerson()
        product = self.factory.makeProduct()
        namespace = ProductNamespace(person, product)
        self.assertEqual(person, removeSecurityProxy(namespace).owner)


class TestProductNamespacePrivacy(TestCaseWithFactory):
    """Tests for the privacy aspects of `ProductNamespace`."""

    layer = DatabaseFunctionalLayer

    def test_subscriber(self):
        # If there is no privacy policy, then there is no privacy subscriber.
        person = self.factory.makePerson()
        product = self.factory.makeProduct()
        namespace = ProductNamespace(person, product)
        self.assertIs(None, namespace.getPrivacySubscriber())

    def test_subscriber_private_team_personal_namespace(self):
        # If there is a private policy for a team that the registrant is in,
        # and the namespace owner is in that team, then the team is
        # subscribed.
        person = self.factory.makePerson()
        product = self.factory.makeProduct()
        namespace = ProductNamespace(person, product)
        team = self.factory.makeTeam(owner=person)
        product.setBranchVisibilityTeamPolicy(
            team, BranchVisibilityRule.PRIVATE)
        self.assertEqual(team, namespace.getPrivacySubscriber())

    def test_subscriber_private_team_namespace(self):
        # If there is a private policy for a namespace owner, then there is no
        # privacy subscriber.
        person = self.factory.makePerson()
        team = self.factory.makeTeam(owner=person)
        product = self.factory.makeProduct()
        namespace = ProductNamespace(team, product)
        product.setBranchVisibilityTeamPolicy(
            team, BranchVisibilityRule.PRIVATE)
        self.assertIs(None, namespace.getPrivacySubscriber())

    def test_subscriber_personal_namespace_multiple_rules(self):
        # If the namespace owner is a member of multiple teams that have
        # private rules, there is no privacy subscriber.
        person = self.factory.makePerson()
        product = self.factory.makeProduct()
        namespace = ProductNamespace(person, product)
        product.setBranchVisibilityTeamPolicy(
            self.factory.makeTeam(owner=person), BranchVisibilityRule.PRIVATE)
        product.setBranchVisibilityTeamPolicy(
            self.factory.makeTeam(owner=person), BranchVisibilityRule.PRIVATE)
        self.assertIs(None, namespace.getPrivacySubscriber())

    def test_subscriber_personal_namespace_diverse_rules(self):
        # If the namespace owner is a member of multiple teams and only one of
        # those rules is private, then the team that has the private rule is
        # the subscriber.
        person = self.factory.makePerson()
        product = self.factory.makeProduct()
        namespace = ProductNamespace(person, product)
        product.setBranchVisibilityTeamPolicy(
            self.factory.makeTeam(owner=person), BranchVisibilityRule.PUBLIC)
        product.setBranchVisibilityTeamPolicy(
            self.factory.makeTeam(owner=person), BranchVisibilityRule.PUBLIC)
        team = self.factory.makeTeam(owner=person)
        product.setBranchVisibilityTeamPolicy(
            team, BranchVisibilityRule.PRIVATE)
        self.assertEqual(team, namespace.getPrivacySubscriber())


class TestPackageNamespace(TestCaseWithFactory, NamespaceMixin):
    """Tests for `PackageNamespace`."""

    layer = DatabaseFunctionalLayer

    def getNamespace(self):
        return get_branch_namespace(
            person=self.factory.makePerson(),
            distroseries=self.factory.makeDistroRelease(),
            sourcepackagename=self.factory.makeSourcePackageName())

    def test_name(self):
        # A package namespace has branches that start with
        # ~foo/ubuntu/spicy/packagename.
        person = self.factory.makePerson()
        distroseries = self.factory.makeDistroRelease()
        sourcepackagename = self.factory.makeSourcePackageName()
        namespace = PackageNamespace(
            person, SourcePackage(sourcepackagename, distroseries))
        self.assertEqual(
            '~%s/%s/%s/%s' % (
                person.name, distroseries.distribution.name,
                distroseries.name, sourcepackagename.name),
            namespace.name)

    def test_owner(self):
        # The person passed to a package namespace is the owner.
        person = self.factory.makePerson()
        distroseries = self.factory.makeDistroRelease()
        sourcepackagename = self.factory.makeSourcePackageName()
        namespace = PackageNamespace(
            person, SourcePackage(sourcepackagename, distroseries))
        self.assertEqual(person, removeSecurityProxy(namespace).owner)


class TestPackageNamespacePrivacy(TestCaseWithFactory):
    """Tests for the privacy aspects of `PackageNamespace`."""

    layer = DatabaseFunctionalLayer

    def test_subscriber(self):
        # There are no implicit subscribers for a personal namespace.
        person = self.factory.makePerson()
        distroseries = self.factory.makeDistroRelease()
        sourcepackagename = self.factory.makeSourcePackageName()
        namespace = PackageNamespace(
            person, SourcePackage(sourcepackagename, distroseries))
        self.assertIs(None, namespace.getPrivacySubscriber())


class TestNamespaceSet(TestCaseWithFactory):
    """Tests for `get_namespace`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.namespace_set = getUtility(IBranchNamespaceSet)

    def test_get_personal(self):
        person = self.factory.makePerson()
        namespace = get_branch_namespace(person=person)
        self.assertIsInstance(namespace, PersonalNamespace)

    def test_get_product(self):
        person = self.factory.makePerson()
        product = self.factory.makeProduct()
        namespace = get_branch_namespace(person=person, product=product)
        self.assertIsInstance(namespace, ProductNamespace)

    def test_get_package(self):
        person = self.factory.makePerson()
        distroseries = self.factory.makeDistroRelease()
        sourcepackagename = self.factory.makeSourcePackageName()
        namespace = get_branch_namespace(
            person=person, distroseries=distroseries,
            sourcepackagename=sourcepackagename)
        self.assertIsInstance(namespace, PackageNamespace)

    def test_lookup_personal(self):
        # lookup_branch_namespace returns a personal namespace if given a junk
        # path.
        person = self.factory.makePerson()
        namespace = lookup_branch_namespace('~%s/+junk' % person.name)
        self.assertIsInstance(namespace, PersonalNamespace)
        self.assertEqual(person, removeSecurityProxy(namespace).owner)

    def test_lookup_personal_not_found(self):
        # lookup_branch_namespace raises NoSuchPerson error if the given
        # person doesn't exist.
        self.assertRaises(
            NoSuchPerson, lookup_branch_namespace, '~no-such-person/+junk')

    def test_lookup_product(self):
        person = self.factory.makePerson()
        product = self.factory.makeProduct()
        namespace = lookup_branch_namespace(
            '~%s/%s' % (person.name, product.name))
        self.assertIsInstance(namespace, ProductNamespace)
        self.assertEqual(person, removeSecurityProxy(namespace).owner)
        self.assertEqual(product, removeSecurityProxy(namespace).product)

    def test_lookup_product_not_found(self):
        person = self.factory.makePerson()
        self.assertRaises(
            NoSuchProduct, lookup_branch_namespace,
            '~%s/no-such-product' % person.name)

    def test_lookup_package(self):
        person = self.factory.makePerson()
        sourcepackage = self.factory.makeSourcePackage()
        namespace = lookup_branch_namespace(
            '~%s/%s' % (person.name, sourcepackage.path))
        self.assertIsInstance(namespace, PackageNamespace)
        self.assertEqual(person, removeSecurityProxy(namespace).owner)
        namespace = removeSecurityProxy(namespace)
        self.assertEqual(sourcepackage, namespace.sourcepackage)

    def test_lookup_package_no_distribution(self):
        person = self.factory.makePerson()
        self.assertRaises(
            NoSuchDistribution, lookup_branch_namespace,
            '~%s/no-such-distro/whocares/whocares' % person.name)

    def test_lookup_package_no_distroseries(self):
        person = self.factory.makePerson()
        distribution = self.factory.makeDistribution()
        self.assertRaises(
            NoSuchDistroSeries, lookup_branch_namespace,
            '~%s/%s/no-such-series/whocares'
            % (person.name, distribution.name))

    def test_lookup_package_no_source_package(self):
        person = self.factory.makePerson()
        distroseries = self.factory.makeDistroRelease()
        self.assertRaises(
            NoSuchSourcePackageName, lookup_branch_namespace,
            '~%s/%s/%s/no-such-spn' % (
                person.name, distroseries.distribution.name,
                distroseries.name))

    def assertInvalidName(self, name):
        """Assert that 'name' is an invalid namespace name."""
        self.assertRaises(InvalidNamespace, self.namespace_set.parse, name)

    def test_lookup_invalid_name(self):
        # Namespace paths must start with a tilde. Thus, lookup will raise an
        # InvalidNamespace error if it is given a path without one.
        person = self.factory.makePerson()
        self.assertInvalidName(person.name)

    def test_lookup_short_name_person_only(self):
        # Given a path that only has a person in it, lookup will raise an
        # InvalidNamespace error.
        person = self.factory.makePerson()
        self.assertInvalidName('~' + person.name)

    def test_lookup_short_name_person_and_distro(self):
        # We can't tell the difference between ~user/distro,
        # ~user/no-such-product and ~user/no-such-distro, so we just raise
        # NoSuchProduct, which is perhaps the most common case.
        person = self.factory.makePerson()
        distroseries = self.factory.makeDistroRelease()
        self.assertRaises(
            NoSuchProduct, lookup_branch_namespace,
            '~%s/%s' % (person.name, distroseries.distribution.name))

    def test_lookup_short_name_distroseries(self):
        # Given a too-short path to a package branch namespace, lookup will
        # raise an InvalidNamespace error.
        person = self.factory.makePerson()
        distroseries = self.factory.makeDistroRelease()
        self.assertInvalidName(
            '~%s/%s/%s' % (
                person.name, distroseries.distribution.name,
                distroseries.name))

    def test_lookup_long_name_junk(self):
        # Given a too-long personal path, lookup will raise an
        # InvalidNamespace error.
        person = self.factory.makePerson()
        self.assertInvalidName('~%s/+junk/foo' % person.name)

    def test_lookup_long_name_product(self):
        # Given a too-long product path, lookup will raise an InvalidNamespace
        # error.
        person = self.factory.makePerson()
        product = self.factory.makeProduct()
        self.assertInvalidName('~%s/%s/foo' % (person.name, product.name))

    def test_lookup_long_name_sourcepackage(self):
        # Given a too-long name, lookup will raise an InvalidNamespace error.
        person = self.factory.makePerson()
        distroseries = self.factory.makeDistroRelease()
        sourcepackagename = self.factory.makeSourcePackageName()
        self.assertInvalidName(
            '~%s/%s/%s/%s/foo' % (
                person.name, distroseries.distribution.name,
                distroseries.name, sourcepackagename.name))

    def test_parse_junk_namespace(self):
        # parse takes a path to a personal (i.e. junk) branch namespace and
        # returns a dict that has the person field set but all others set to
        # None.
        self.assertEqual(
            dict(person='foo', product='+junk', distroseries=None,
                 distribution=None, sourcepackagename=None),
            self.namespace_set.parse('~foo/+junk'))

    def test_parse_product_namespace(self):
        # parse take a path to a product branch namespace and returns a dict
        # with the product set and the distro-related keys set to None.
        self.assertEqual(
            dict(person='foo', product='bar', distroseries=None,
                 distribution=None, sourcepackagename=None),
            self.namespace_set.parse('~foo/bar'))

    def test_parse_package_namespace(self):
        # parse takes a path to a package branch namespace and returns a dict
        # with the distro-related keys populated, and the product set to None.
        self.assertEqual(
            dict(person='foo', product=None, distribution='ubuntu',
                 distroseries='jaunty', sourcepackagename='foo'),
            self.namespace_set.parse('~foo/ubuntu/jaunty/foo'))

    def test_parseBranchPath_junk_path(self):
        # parseBranchPath takes a path within a branch and returns the dict of
        # the namespace that it's in, as well as the part of the path that is
        # within the namespace.
        path = '~foo/+junk/bar/README'
        parse_results = list(self.namespace_set.parseBranchPath(path))
        expected_results = [
            (dict(person='foo', product='+junk', distribution=None,
                  distroseries=None, sourcepackagename=None),
             'bar', 'README')]
        self.assertEqual(expected_results, parse_results)

    def test_parseBranchPath_product_path(self):
        path = '~foo/bar/baz/README'
        parse_results = list(self.namespace_set.parseBranchPath(path))
        expected_results = [
            (dict(person='foo', product='bar', distribution=None,
                  distroseries=None, sourcepackagename=None),
             'baz', 'README')]
        self.assertEqual(expected_results, parse_results)

    def test_parseBranchPath_package_path(self):
        path = '~foo/bar/baz/qux/branch/README'
        parse_results = list(self.namespace_set.parseBranchPath(path))
        expected_results = [
            (dict(person='foo', product=None, distribution='bar',
                  distroseries='baz', sourcepackagename='qux'), 'branch',
             'README'),
            (dict(person='foo', product='bar', distribution=None,
                  distroseries=None, sourcepackagename=None), 'baz',
             'qux/branch/README')]
        self.assertEqual(sorted(expected_results), sorted(parse_results))

    def test_parseBranchPath_invalid_path(self):
        path = 'foo/bar/baz/qux/branch/README'
        self.assertRaises(
            InvalidNamespace, list, self.namespace_set.parseBranchPath(path))

    def test_parseBranchPath_empty(self):
        self.assertRaises(
            InvalidNamespace, list, self.namespace_set.parseBranchPath(''))

    def test_interpret_product_aliases(self):
        # Products can have aliases. IBranchNamespaceSet.interpret will find a
        # product given its alias.
        branch = self.factory.makeProductBranch()
        product_alias = self.factory.getUniqueString()
        removeSecurityProxy(branch.product).setAliases([product_alias])
        namespace = self.namespace_set.interpret(
            branch.owner.name, product=product_alias)
        self.assertEqual(
            branch.product, removeSecurityProxy(namespace).product)

    def _getSegments(self, branch):
        """Return an iterable of the branch name segments.

        Note that the person element is *not* proceeded by a tilde.
        """
        return iter(branch.unique_name[1:].split('/'))

    def test_traverse_junk_branch(self):
        # IBranchNamespaceSet.traverse returns a branch based on an iterable
        # of path segments, including junk branches.
        branch = self.factory.makePersonalBranch()
        segments = self._getSegments(branch)
        found_branch = self.namespace_set.traverse(segments)
        self.assertEqual(branch, found_branch)

    def test_traverse_junk_branch_not_found(self):
        person = self.factory.makePerson()
        segments = iter([person.name, '+junk', 'no-such-branch'])
        self.assertRaises(
            NoSuchBranch, self.namespace_set.traverse, segments)
        self.assertEqual([], list(segments))

    def test_traverse_person_not_found(self):
        segments = iter(['no-such-person', 'whatever'])
        self.assertRaises(
            NoSuchPerson, self.namespace_set.traverse, segments)
        self.assertEqual(['whatever'], list(segments))

    def test_traverse_product_branch(self):
        # IBranchNamespaceSet.traverse returns a branch based on an iterable
        # of path segments, including product branches.
        branch = self.factory.makeProductBranch()
        segments = self._getSegments(branch)
        found_branch = self.namespace_set.traverse(segments)
        self.assertEqual(branch, found_branch)

    def test_traverse_project_branch(self):
        # IBranchNamespaceSet.traverse raises NoSuchProduct if the product is
        # actually a project.
        person = self.factory.makePerson()
        project = self.factory.makeProject()
        segments = iter([person.name, project.name, 'branch'])
        self.assertRaises(
            NoSuchProduct, self.namespace_set.traverse, segments)

    def test_traverse_package_branch(self):
        # IBranchNamespaceSet.traverse returns a branch based on an iterable
        # of path segments, including package branches.
        branch = self.factory.makePackageBranch()
        segments = self._getSegments(branch)
        found_branch = self.namespace_set.traverse(segments)
        self.assertEqual(branch, found_branch)

    def test_traverse_product_not_found(self):
        # IBranchNamespaceSet.traverse raises NoSuchProduct if it cannot find
        # the product.
        person = self.factory.makePerson()
        segments = iter([person.name, 'no-such-product', 'branch'])
        self.assertRaises(
            NoSuchProduct, self.namespace_set.traverse, segments)
        self.assertEqual(['branch'], list(segments))

    def test_traverse_package_branch_aliases(self):
        # Distributions can have aliases. IBranchNamespaceSet.traverse will
        # find a branch where its distro is given as an alias.
        branch = self.factory.makePackageBranch()
        pillar_alias = self.factory.getUniqueString()
        removeSecurityProxy(branch.distribution).setAliases([pillar_alias])
        segments = iter([
            branch.owner.name, pillar_alias, branch.distroseries.name,
            branch.sourcepackagename.name, branch.name,
            ])
        found_branch = self.namespace_set.traverse(segments)
        self.assertEqual(branch, found_branch)

    def test_traverse_distribution_not_found(self):
        # IBranchNamespaceSet.traverse raises NoSuchProduct if it cannot find
        # the distribution. We do this since we can't tell the difference
        # between a non-existent product and a non-existent distro.
        person = self.factory.makePerson()
        segments = iter(
            [person.name, 'no-such-distro', 'jaunty', 'evolution', 'branch'])
        self.assertRaises(
            NoSuchProduct, self.namespace_set.traverse, segments)
        self.assertEqual(['jaunty', 'evolution', 'branch'], list(segments))

    def test_traverse_distroseries_not_found(self):
        person = self.factory.makePerson()
        distro = self.factory.makeDistribution()
        segments = iter(
            [person.name, distro.name, 'no-such-series', 'package', 'branch'])
        self.assertRaises(
            NoSuchDistroSeries, self.namespace_set.traverse, segments)
        self.assertEqual(['package', 'branch'], list(segments))

    def test_traverse_sourcepackagename_not_found(self):
        person = self.factory.makePerson()
        distroseries = self.factory.makeDistroRelease()
        distro = distroseries.distribution
        segments = iter(
            [person.name, distro.name, distroseries.name, 'no-such-package',
             'branch'])
        self.assertRaises(
            NoSuchSourcePackageName, self.namespace_set.traverse, segments)
        self.assertEqual(['branch'], list(segments))

    def test_traverse_leaves_trailing_segments(self):
        # traverse doesn't consume all the elements of the iterable. It only
        # consumes those it needs to find a branch.
        branch = self.factory.makeAnyBranch()
        trailing_segments = ['+foo', 'bar']
        segments = iter(branch.unique_name[1:].split('/') + trailing_segments)
        found_branch = self.namespace_set.traverse(segments)
        self.assertEqual(branch, found_branch)
        self.assertEqual(trailing_segments, list(segments))

    def test_too_few_segments(self):
        # If there aren't enough segments, raise InvalidNamespace.
        person = self.factory.makePerson()
        self.assertRaises(
            InvalidNamespace,
            self.namespace_set.traverse, iter([person.name]))

    def test_last_segment_none(self):
        # If the last name passed to traverse is None, raise an error (rather
        # than returning None).
        person = self.factory.makePerson()
        product = self.factory.makeProduct()
        self.assertRaises(
            AssertionError,
            self.namespace_set.traverse,
            iter([person.name, product.name, None]))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
