# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `IBranchNamespace` implementations."""

__metaclass__ = type

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.validators import LaunchpadValidationError
from lp.code.enums import (
    BranchLifecycleStatus,
    BranchType,
    BranchVisibilityRule,
    )
from lp.code.errors import (
    BranchCreationForbidden,
    BranchCreatorNotMemberOfOwnerTeam,
    BranchCreatorNotOwner,
    BranchExists,
    InvalidNamespace,
    NoSuchBranch,
    )
from lp.code.interfaces.branchnamespace import (
    get_branch_namespace,
    IBranchNamespace,
    IBranchNamespacePolicy,
    IBranchNamespaceSet,
    lookup_branch_namespace,
    )
from lp.code.interfaces.branchtarget import IBranchTarget
from lp.code.model.branchnamespace import (
    PackageNamespace,
    PersonalNamespace,
    ProductNamespace,
    )
from lp.registry.errors import (
    NoSuchDistroSeries,
    NoSuchSourcePackageName,
    )
from lp.registry.interfaces.distribution import NoSuchDistribution
from lp.registry.interfaces.person import NoSuchPerson
from lp.registry.interfaces.product import NoSuchProduct
from lp.registry.model.sourcepackage import SourcePackage
from lp.testing import TestCaseWithFactory


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
        # createBranch takes all the arguments that the `Branch` constructor
        # takes, except for the ones that define the namespace.
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
        self.assertEqual(
            BranchLifecycleStatus.EXPERIMENTAL, branch.lifecycle_status)
        self.assertEqual(whiteboard, branch.whiteboard)

    def test_createBranch_subscribes_owner(self):
        owner = self.factory.makeTeam()
        namespace = self.getNamespace(owner)
        branch_name = self.factory.getUniqueString()
        registrant = owner.teamowner
        branch = namespace.createBranch(
            BranchType.HOSTED, branch_name, registrant)
        self.assertEqual([owner], list(branch.subscribers))

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
        namespace.createBranch(
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

    def test_validateMove(self):
        # If the mover is allowed to move the branch into the namespace, if
        # there are absolutely no problems at all, then validateMove raises
        # nothing and returns None.
        namespace = self.getNamespace()
        namespace_owner = removeSecurityProxy(namespace).owner
        branch = self.factory.makeAnyBranch()
        # Doesn't raise an exception.
        self.assertIs(None, namespace.validateMove(branch, namespace_owner))

    def test_validateMove_branch_with_name_exists(self):
        # If a branch with the same name as the given branch already exists in
        # the namespace, validateMove raises a BranchExists error.
        namespace = self.getNamespace()
        namespace_owner = removeSecurityProxy(namespace).owner
        name = self.factory.getUniqueString()
        namespace.createBranch(
            BranchType.HOSTED, name, removeSecurityProxy(namespace).owner)
        branch = self.factory.makeAnyBranch(name=name)
        self.assertRaises(
            BranchExists, namespace.validateMove, branch, namespace_owner)

    def test_validateMove_forbidden_owner(self):
        # If the mover isn't allowed to create branches in the namespace, then
        # they aren't allowed to move branches in there either, so
        # validateMove wil raise a BranchCreatorNotOwner error.
        namespace = self.getNamespace()
        branch = self.factory.makeAnyBranch()
        mover = self.factory.makePerson()
        self.assertRaises(
            BranchCreatorNotOwner, namespace.validateMove, branch, mover)

    def test_validateMove_not_team_member(self):
        # If the mover isn't allowed to create branches in the namespace
        # because they aren't a member of the team that owns the namespace,
        # validateMove raises a BranchCreatorNotMemberOfOwnerTeam error.
        team = self.factory.makeTeam()
        namespace = self.getNamespace(person=team)
        branch = self.factory.makeAnyBranch()
        mover = self.factory.makePerson()
        self.assertRaises(
            BranchCreatorNotMemberOfOwnerTeam,
            namespace.validateMove, branch, mover)

    def test_validateMove_with_other_name(self):
        # If you pass a name to validateMove, that'll check to see whether the
        # branch could be safely moved given a rename.
        namespace = self.getNamespace()
        namespace_owner = removeSecurityProxy(namespace).owner
        name = self.factory.getUniqueString()
        namespace.createBranch(
            BranchType.HOSTED, name, removeSecurityProxy(namespace).owner)
        branch = self.factory.makeAnyBranch()
        self.assertRaises(
            BranchExists, namespace.validateMove, branch, namespace_owner,
            name=name)


class TestPersonalNamespace(TestCaseWithFactory, NamespaceMixin):
    """Tests for `PersonalNamespace`."""

    layer = DatabaseFunctionalLayer

    def getNamespace(self, person=None):
        if person is None:
            person = self.factory.makePerson()
        return get_branch_namespace(person=person)

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

    def test_target(self):
        # The target of a personal namespace is the branch target of the owner
        # of that namespace.
        person = self.factory.makePerson()
        namespace = PersonalNamespace(person)
        self.assertEqual(IBranchTarget(person), namespace.target)


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

    def getNamespace(self, person=None):
        if person is None:
            person = self.factory.makePerson()
        return get_branch_namespace(
            person=person, product=self.factory.makeProduct())

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

    def test_target(self):
        # The target for a product namespace is the branch target of the
        # product.
        person = self.factory.makePerson()
        product = self.factory.makeProduct()
        namespace = ProductNamespace(person, product)
        self.assertEqual(IBranchTarget(product), namespace.target)


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

    def getNamespace(self, person=None):
        if person is None:
            person = self.factory.makePerson()
        return get_branch_namespace(
            person=person,
            distroseries=self.factory.makeDistroSeries(),
            sourcepackagename=self.factory.makeSourcePackageName())

    def test_name(self):
        # A package namespace has branches that start with
        # ~foo/ubuntu/spicy/packagename.
        person = self.factory.makePerson()
        distroseries = self.factory.makeDistroSeries()
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
        distroseries = self.factory.makeDistroSeries()
        sourcepackagename = self.factory.makeSourcePackageName()
        namespace = PackageNamespace(
            person, SourcePackage(sourcepackagename, distroseries))
        self.assertEqual(person, removeSecurityProxy(namespace).owner)

    def test_target(self):
        # The target for a package namespace is the branch target of the
        # sourcepackage.
        person = self.factory.makePerson()
        package = self.factory.makeSourcePackage()
        namespace = PackageNamespace(person, package)
        self.assertEqual(IBranchTarget(package), namespace.target)


class TestPackageNamespacePrivacy(TestCaseWithFactory):
    """Tests for the privacy aspects of `PackageNamespace`."""

    layer = DatabaseFunctionalLayer

    def test_subscriber(self):
        # There are no implicit subscribers for a personal namespace.
        person = self.factory.makePerson()
        distroseries = self.factory.makeDistroSeries()
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
        distroseries = self.factory.makeDistroSeries()
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
        distroseries = self.factory.makeDistroSeries()
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
        distroseries = self.factory.makeDistroSeries()
        self.assertRaises(
            NoSuchProduct, lookup_branch_namespace,
            '~%s/%s' % (person.name, distroseries.distribution.name))

    def test_lookup_short_name_distroseries(self):
        # Given a too-short path to a package branch namespace, lookup will
        # raise an InvalidNamespace error.
        person = self.factory.makePerson()
        distroseries = self.factory.makeDistroSeries()
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
        distroseries = self.factory.makeDistroSeries()
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
        distroseries = self.factory.makeDistroSeries()
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


class BaseCanCreateBranchesMixin:
    """Common tests for all namespaces."""

    layer = DatabaseFunctionalLayer

    def _getNamespace(self, owner):
        # Return a namespace appropriate for the owner specified.
        raise NotImplementedError(self._getNamespace)

    def test_individual(self):
        # For a BranchTarget for an individual, only the individual can own
        # branches there.
        person = self.factory.makePerson()
        namespace = self._getNamespace(person)
        self.assertTrue(namespace.canCreateBranches(person))

    def test_other_user(self):
        # Any other individual cannot own branches targeted to the person.
        person = self.factory.makePerson()
        namespace = self._getNamespace(person)
        self.assertFalse(
            namespace.canCreateBranches(self.factory.makePerson()))

    def test_team_member(self):
        # A member of a team is able to create a branch on this namespace.
        # This is a team junk branch.
        person = self.factory.makePerson()
        self.factory.makeTeam(owner=person)
        namespace = self._getNamespace(person)
        self.assertTrue(namespace.canCreateBranches(person))

    def test_team_non_member(self):
        # A person who is not part of the team cannot create branches for the
        # personal team target.
        person = self.factory.makePerson()
        self.factory.makeTeam(owner=person)
        namespace = self._getNamespace(person)
        self.assertFalse(
            namespace.canCreateBranches(self.factory.makePerson()))


class TestPersonalNamespaceCanCreateBranches(TestCaseWithFactory,
                                             BaseCanCreateBranchesMixin):

    def _getNamespace(self, owner):
        return PersonalNamespace(owner)


class TestPackageNamespaceCanCreateBranches(TestCaseWithFactory,
                                            BaseCanCreateBranchesMixin):

    def _getNamespace(self, owner):
        source_package = self.factory.makeSourcePackage()
        return PackageNamespace(owner, source_package)


class TestProductNamespaceCanCreateBranches(TestCaseWithFactory,
                                            BaseCanCreateBranchesMixin):

    def _getNamespace(self, owner):
        product = self.factory.makeProduct()
        return ProductNamespace(owner, product)

    def setUp(self):
        # Setting visibility policies is an admin only task.
        TestCaseWithFactory.setUp(self, 'admin@canonical.com')

    def test_any_person(self):
        # If there is no privacy set up, any person can create a personal
        # branch on the product.
        person = self.factory.makePerson()
        namespace = self._getNamespace(person)
        self.assertTrue(namespace.canCreateBranches(person))

    def test_any_person_with_public_base_rule(self):
        # If the base visibility rule is PUBLIC, then anyone can create a
        # personal branch.
        person = self.factory.makePerson()
        namespace = self._getNamespace(person)
        namespace.product.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.PUBLIC)
        self.assertTrue(namespace.canCreateBranches(person))

    def test_any_person_with_forbidden_base_rule(self):
        # If the base visibility rule is FORBIDDEN, then non-privleged users
        # canot create a branch.
        person = self.factory.makePerson()
        namespace = self._getNamespace(person)
        namespace.product.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.FORBIDDEN)
        self.assertFalse(namespace.canCreateBranches(person))

    def assertTeamMemberCanCreateBranches(self, policy_rule):
        # Create a product with a team policy with the specified rule, and
        # make sure that the team member can create branches.
        person = self.factory.makePerson()
        namespace = self._getNamespace(person)
        namespace.product.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.FORBIDDEN)
        team = self.factory.makeTeam(owner=person)
        namespace.product.setBranchVisibilityTeamPolicy(team, policy_rule)
        self.assertTrue(namespace.canCreateBranches(person))

    def test_team_member_public_policy(self):
        # A person in a team with a PUBLIC rule can create branches even if
        # the base rule is FORBIDDEN.
        self.assertTeamMemberCanCreateBranches(BranchVisibilityRule.PUBLIC)

    def test_team_member_private_policy(self):
        # A person in a team with a PRIVATE rule can create branches even if
        # the base rule is FORBIDDEN.
        self.assertTeamMemberCanCreateBranches(BranchVisibilityRule.PRIVATE)

    def test_team_member_private_only_policy(self):
        # A person in a team with a PRIVATE_ONLY rule can create branches even
        # if the base rule is FORBIDDEN.
        self.assertTeamMemberCanCreateBranches(
            BranchVisibilityRule.PRIVATE_ONLY)


class TestPersonalNamespaceCanBranchesBePrivate(TestCaseWithFactory):
    """Tests for PersonalNamespace.canBranchesBePrivate."""

    layer = DatabaseFunctionalLayer

    def test_anyone(self):
        # No +junk branches are private.
        person = self.factory.makePerson()
        namespace = PersonalNamespace(person)
        self.assertFalse(namespace.canBranchesBePrivate())


class TestPersonalNamespaceCanBranchesBePublic(TestCaseWithFactory):
    """Tests for PersonalNamespace.canBranchesBePublic."""

    layer = DatabaseFunctionalLayer

    def test_anyone(self):
        # All +junk branches are public.
        person = self.factory.makePerson()
        namespace = PersonalNamespace(person)
        self.assertTrue(namespace.canBranchesBePublic())


class TestPackageNamespaceCanBranchesBePrivate(TestCaseWithFactory):
    """Tests for PackageNamespace.canBranchesBePrivate."""

    layer = DatabaseFunctionalLayer

    def test_anyone(self):
        # No source package branches are private.
        source_package = self.factory.makeSourcePackage()
        person = self.factory.makePerson()
        namespace = PackageNamespace(person, source_package)
        self.assertFalse(namespace.canBranchesBePrivate())


class TestPackageNamespaceCanBranchesBePublic(TestCaseWithFactory):
    """Tests for PackageNamespace.canBranchesBePublic."""

    layer = DatabaseFunctionalLayer

    def test_anyone(self):
        # All source package branches are public.
        source_package = self.factory.makeSourcePackage()
        person = self.factory.makePerson()
        namespace = PackageNamespace(person, source_package)
        self.assertTrue(namespace.canBranchesBePublic())


class TestProductNamespaceCanBranchesBePrivate(TestCaseWithFactory):
    """Tests for ProductNamespace.canBranchesBePrivate."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.product = self.factory.makeProduct()

    def _getNamespace(self, owner):
        return ProductNamespace(owner, self.product)

    def assertNewBranchesPublic(self, owner):
        # Assert that new branches in the owner namespace are public.
        namespace = self._getNamespace(owner)
        self.assertFalse(namespace.canBranchesBePrivate())

    def assertNewBranchesPrivate(self, owner):
        # Assert that new branches in the owner namespace are private.
        namespace = self._getNamespace(owner)
        self.assertTrue(namespace.canBranchesBePrivate())

    def test_no_policies(self):
        # If there are no defined policies, any personal branch is not
        # private.
        self.assertNewBranchesPublic(self.factory.makePerson())

    def test_any_person_with_public_base_rule(self):
        # If the base visibility rule is PUBLIC, then new branches are public.
        self.product.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.PUBLIC)
        self.assertNewBranchesPublic(self.factory.makePerson())

    def test_any_person_with_forbidden_base_rule(self):
        # If the base visibility rule is FORBIDDEN, new branches are still
        # considered public.
        self.product.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.FORBIDDEN)
        self.assertNewBranchesPublic(self.factory.makePerson())

    def test_team_member_with_private_rule(self):
        # If a person is a member of a team that has a PRIVATE rule, then new
        # branches are private in either the person or team namespace.
        person = self.factory.makePerson()
        team = self.factory.makeTeam(owner=person)
        self.product.setBranchVisibilityTeamPolicy(
            team, BranchVisibilityRule.PRIVATE)
        self.assertNewBranchesPrivate(person)
        self.assertNewBranchesPrivate(team)

    def test_team_member_with_private_only_rule(self):
        # If a person is a member of a team that has a PRIVATE_ONLY rule, then
        # new branches are private in either the person or team namespace.
        person = self.factory.makePerson()
        team = self.factory.makeTeam(owner=person)
        self.product.setBranchVisibilityTeamPolicy(
            team, BranchVisibilityRule.PRIVATE_ONLY)
        self.assertNewBranchesPrivate(person)
        self.assertNewBranchesPrivate(team)

    def test_non_team_member_with_private_rule(self):
        # If a person is a not a member of a team that has a privacy rule,
        # then new branches are public.
        person = self.factory.makePerson()
        team = self.factory.makeTeam(owner=person)
        self.product.setBranchVisibilityTeamPolicy(
            team, BranchVisibilityRule.PRIVATE)
        self.assertNewBranchesPublic(self.factory.makePerson())

    def test_team_member_with_multiple_private_rules(self):
        # If a person is a member of multiple teams that has a privacy rules,
        # then new branches are private in all options.
        person = self.factory.makePerson()
        team_1 = self.factory.makeTeam(owner=person)
        team_2 = self.factory.makeTeam(owner=person)
        self.product.setBranchVisibilityTeamPolicy(
            team_1, BranchVisibilityRule.PRIVATE)
        self.product.setBranchVisibilityTeamPolicy(
            team_2, BranchVisibilityRule.PRIVATE)
        self.assertNewBranchesPrivate(person)
        self.assertNewBranchesPrivate(team_1)
        self.assertNewBranchesPrivate(team_2)

    def test_team_member_with_multiple_differing_private_rules(self):
        # If a person is a member of multiple teams that has a privacy rules,
        # and one rule says PRIVATE and the other PUBLIC, then personal
        # branches will be private, and branches owned by teams with rules
        # will relate to the rule of the team.
        person = self.factory.makePerson()
        private_team = self.factory.makeTeam(owner=person)
        public_team = self.factory.makeTeam(owner=person)
        self.product.setBranchVisibilityTeamPolicy(
            private_team, BranchVisibilityRule.PRIVATE)
        self.product.setBranchVisibilityTeamPolicy(
            public_team, BranchVisibilityRule.PUBLIC)
        self.assertNewBranchesPrivate(person)
        self.assertNewBranchesPrivate(private_team)
        self.assertNewBranchesPublic(public_team)


class TestProductNamespaceCanBranchesBePublic(TestCaseWithFactory):
    """Tests for ProductNamespace.canBranchesBePublic."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.product = self.factory.makeProduct()

    def _getNamespace(self, owner):
        return ProductNamespace(owner, self.product)

    def assertBranchesCanBePublic(self, owner):
        # Assert that branches can be public in the owner namespace.
        namespace = self._getNamespace(owner)
        self.assertTrue(namespace.canBranchesBePublic())

    def assertBranchesMustBePrivate(self, owner):
        # Assert that branches must be private in the owner namespace.
        namespace = self._getNamespace(owner)
        self.assertFalse(namespace.canBranchesBePublic())

    def test_no_policies(self):
        # If there are no defined policies, any branch can be public.
        self.assertBranchesCanBePublic(self.factory.makePerson())

    def test_any_person_with_public_base_rule(self):
        # If the base visibility rule is PUBLIC, any branch can be public
        self.product.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.PUBLIC)
        self.assertBranchesCanBePublic(self.factory.makePerson())

    def test_any_person_with_forbidden_base_rule(self):
        # If the base visibility rule is FORBIDDEN, branches must be private.
        self.product.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.FORBIDDEN)
        self.assertBranchesMustBePrivate(self.factory.makePerson())

    def test_team_member_with_private_rule(self):
        # If a person is a member of a team that has a PRIVATE rule then the
        # branches can be public even though the default is FORBIDDEN.
        person = self.factory.makePerson()
        team = self.factory.makeTeam(owner=person)
        self.product.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.FORBIDDEN)
        self.product.setBranchVisibilityTeamPolicy(
            team, BranchVisibilityRule.PRIVATE)
        self.assertBranchesCanBePublic(person)
        self.assertBranchesCanBePublic(team)

    def test_team_member_with_private_only_rule(self):
        # If a person is a member of a team that has a PRIVATE_ONLY rule, and
        # the base rule is FORBIDDEN, then the branches must be private.
        person = self.factory.makePerson()
        team = self.factory.makeTeam(owner=person)
        self.product.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.FORBIDDEN)
        self.product.setBranchVisibilityTeamPolicy(
            team, BranchVisibilityRule.PRIVATE_ONLY)
        self.assertBranchesMustBePrivate(person)
        self.assertBranchesMustBePrivate(team)

    def test_team_member_with_private_only_rule_public_base_rule(self):
        # If a person is a member of a team that has a PRIVATE_ONLY rule, and
        # the base rule is PUBLIC, then the branches must be private in the
        # team namespace, but can be public in the personal namespace.
        person = self.factory.makePerson()
        team = self.factory.makeTeam(owner=person)
        self.product.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.PUBLIC)
        self.product.setBranchVisibilityTeamPolicy(
            team, BranchVisibilityRule.PRIVATE_ONLY)
        self.assertBranchesCanBePublic(person)
        self.assertBranchesMustBePrivate(team)

    def test_team_member_with_multiple_private_rules(self):
        # If a person is a member of multiple teams that has a privacy rules,
        # then new branches must stay private in any namespace that defines
        # PRIVATE_ONLY, but if the team member is a member of any teams that
        # specify just PRIVATE, then branches can be made public.
        person = self.factory.makePerson()
        team_1 = self.factory.makeTeam(owner=person)
        team_2 = self.factory.makeTeam(owner=person)
        self.product.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.FORBIDDEN)
        self.product.setBranchVisibilityTeamPolicy(
            team_1, BranchVisibilityRule.PRIVATE_ONLY)
        self.product.setBranchVisibilityTeamPolicy(
            team_2, BranchVisibilityRule.PRIVATE)
        self.assertBranchesCanBePublic(person)
        self.assertBranchesMustBePrivate(team_1)
        self.assertBranchesCanBePublic(team_2)


class BaseValidateNewBranchMixin:

    layer = DatabaseFunctionalLayer

    def _getNamespace(self, owner):
        # Return a namespace appropraite for the owner specified.
        raise NotImplementedError(self._getNamespace)

    def test_registrant_not_owner(self):
        # If the namespace owner is an individual, and the registrant is not
        # the owner, BranchCreatorNotOwner is raised.
        namespace = self._getNamespace(self.factory.makePerson())
        self.assertRaises(
            BranchCreatorNotOwner,
            namespace.validateRegistrant,
            self.factory.makePerson())

    def test_registrant_not_in_owner_team(self):
        # If the namespace owner is a team, and the registrant is not
        # in the team, BranchCreatorNotMemberOfOwnerTeam is raised.
        namespace = self._getNamespace(self.factory.makeTeam())
        self.assertRaises(
            BranchCreatorNotMemberOfOwnerTeam,
            namespace.validateRegistrant,
            self.factory.makePerson())

    def test_existing_branch(self):
        # If a branch exists with the same name, then BranchExists is raised.
        namespace = self._getNamespace(self.factory.makePerson())
        branch = namespace.createBranch(
            BranchType.HOSTED, self.factory.getUniqueString(),
            namespace.owner)
        self.assertRaises(
            BranchExists,
            namespace.validateBranchName,
            branch.name)

    def test_invalid_name(self):
        # If the branch name is not valid, a LaunchpadValidationError is
        # raised.
        namespace = self._getNamespace(self.factory.makePerson())
        self.assertRaises(
            LaunchpadValidationError,
            namespace.validateBranchName,
            '+foo')

    def test_permitted_first_character(self):
        # The first character of a branch name must be a letter or a number.
        namespace = self._getNamespace(self.factory.makePerson())
        for c in [chr(i) for i in range(128)]:
            if c.isalnum():
                namespace.validateBranchName(c)
            else:
                self.assertRaises(
                    LaunchpadValidationError,
                    namespace.validateBranchName, c)

    def test_permitted_subsequent_character(self):
        # After the first character, letters, numbers and certain punctuation
        # is permitted.
        namespace = self._getNamespace(self.factory.makePerson())
        for c in [chr(i) for i in range(128)]:
            if c.isalnum() or c in '+-_@.':
                namespace.validateBranchName('a' + c)
            else:
                self.assertRaises(
                    LaunchpadValidationError,
                    namespace.validateBranchName, 'a' + c)


class TestPersonalNamespaceValidateNewBranch(TestCaseWithFactory,
                                             BaseValidateNewBranchMixin):

    def _getNamespace(self, owner):
        return PersonalNamespace(owner)


class TestPackageNamespaceValidateNewBranch(TestCaseWithFactory,
                                            BaseValidateNewBranchMixin):

    def _getNamespace(self, owner):
        source_package = self.factory.makeSourcePackage()
        return PackageNamespace(owner, source_package)


class TestProductNamespaceValidateNewBranch(TestCaseWithFactory,
                                            BaseValidateNewBranchMixin):

    def _getNamespace(self, owner):
        product = self.factory.makeProduct()
        return ProductNamespace(owner, product)


class BranchVisibilityPolicyTestCase(TestCaseWithFactory):
    """Base class for tests to make testing of branch visibility easier."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        """Setup some sample people and teams.

        The team names are: "xray", "yankee", and "zulu".

        The people are:

          * "albert", who is a member of all three teams.
          * "bob", who is a member of yankee.
          * "charlie", who is a member of zulu.
          * "doug", who is a member of no teams.
        """
        TestCaseWithFactory.setUp(self, 'admin@canonical.com')
        # Our test product.
        self.product = self.factory.makeProduct()
        # Create some test people.
        self.albert = self.factory.makePerson(
            email='albert@code.ninja.nz',
            name='albert', displayname='Albert Tester')
        self.bob = self.factory.makePerson(
            email='bob@code.ninja.nz',
            name='bob', displayname='Bob Tester')
        self.charlie = self.factory.makePerson(
            email='charlie@code.ninja.nz',
            name='charlie', displayname='Charlie Tester')
        self.doug = self.factory.makePerson(
            email='doug@code.ninja.nz',
            name='doug', displayname='Doug Tester')

        self.people = (self.albert, self.bob, self.charlie, self.doug)

        # And create some test teams.
        self.xray = self.factory.makeTeam(name='xray')
        self.yankee = self.factory.makeTeam(name='yankee')
        self.zulu = self.factory.makeTeam(name='zulu')
        self.teams = (self.xray, self.yankee, self.zulu)

        # Set the memberships of our test people to the test teams.
        self.albert.join(self.xray)
        self.albert.join(self.yankee)
        self.albert.join(self.zulu)
        self.bob.join(self.yankee)
        self.charlie.join(self.zulu)

    def defineTeamPolicies(self, team_policies):
        """Shortcut to help define team policies."""
        for team, rule in team_policies:
            self.product.setBranchVisibilityTeamPolicy(team, rule)

    def assertBranchRule(self, registrant, owner, expected_rule):
        """Check the getBranchVisibilityRuleForBranch results for a branch."""
        branch = self.factory.makeProductBranch(
            registrant=registrant, owner=owner, product=self.product)
        rule = self.product.getBranchVisibilityRuleForBranch(branch)
        self.assertEqual(rule, expected_rule,
                         'Wrong visibililty rule returned: '
                         'expected %s, got %s'
                         % (expected_rule.name, rule.name))

    def assertPublic(self, creator, owner):
        """Assert that the policy check would result in a public branch.

        :param creator: The user creating the branch.
        :param owner: The person or team that will be the owner of the branch.
        """
        namespace = get_branch_namespace(owner, product=self.product)
        self.assertFalse(namespace.canBranchesBePrivate())

    def assertPrivateSubscriber(self, creator, owner, subscriber):
        """Assert that the policy check results in a private branch.

        :param creator: The user creating the branch.
        :param owner: The person or team that will be the owner of the branch.
        :param subscriber: The expected implicit subscriber to the branch.
        """
        policy = IBranchNamespacePolicy(
            get_branch_namespace(owner, product=self.product))
        self.assertTrue(policy.canBranchesBePrivate())
        if subscriber is None:
            self.assertIs(None, policy.getPrivacySubscriber())
        else:
            self.assertEqual(subscriber, policy.getPrivacySubscriber())

    def assertPolicyCheckRaises(self, error, creator, owner):
        """Assert that the policy check raises an exception.

        :param error: The exception class that should be raised.
        :param creator: The user creating the branch.
        :param owner: The person or team that will be the owner of the branch.
        """
        policy = IBranchNamespacePolicy(
            get_branch_namespace(owner, product=self.product))
        self.assertRaises(
            error,
            policy.validateRegistrant,
            registrant=creator)


class TestTeamMembership(BranchVisibilityPolicyTestCase):
    """Assert the expected team memberhsip of the test users."""

    def test_team_memberships(self):
        albert, bob, charlie, doug = self.people
        xray, yankee, zulu = self.teams
        # Albert is a member of all three teams.
        self.failUnless(albert.inTeam(xray),
                        "Albert should be in team Xray team.")
        self.failUnless(albert.inTeam(yankee),
                        "Albert should be in the Yankee.")
        self.failUnless(albert.inTeam(zulu),
                        "Albert should be in Zulu team.")
        # Bob is a member of only Yankee.
        self.failIf(bob.inTeam(xray),
                    "Bob should not be in team Xray team.")
        self.failUnless(bob.inTeam(yankee),
                        "Bob should be in the Yankee team.")
        self.failIf(bob.inTeam(zulu),
                    "Bob should not be in the Zulu team.")
        # Charlie is a member of only Zulu.
        self.failIf(charlie.inTeam(xray),
                    "Charlie should not be in team Xray team.")
        self.failIf(charlie.inTeam(yankee),
                    "Charlie should not be in the Yankee team.")
        self.failUnless(charlie.inTeam(zulu),
                        "Charlie should be in the Zulu team.")
        # Doug is not a member of any
        self.failIf(doug.inTeam(xray),
                    "Doug should not be in team Xray team.")
        self.failIf(doug.inTeam(yankee),
                    "Doug should not be in the Yankee team.")
        self.failIf(doug.inTeam(zulu),
                    "Doug should not be in the Zulu team.")


class NoPolicies(BranchVisibilityPolicyTestCase):
    """Test behaviour with no team policies defined."""

    def test_creation_where_not_team_member(self):
        """If the creator isn't a member of the owner an exception is raised.
        """
        self.assertPolicyCheckRaises(
            BranchCreatorNotMemberOfOwnerTeam, self.doug, self.xray)

    def test_creation_under_different_user(self):
        """If the owner is a user other than the creator an exception is
        raised.
        """
        self.assertPolicyCheckRaises(
            BranchCreatorNotOwner, self.albert, self.bob)

    def test_public_branch_creation(self):
        """Branches where the creator is a memeber of owner will be public."""
        albert, bob, charlie, doug = self.people
        xray, yankee, zulu = self.teams

        self.assertPublic(albert, albert)
        self.assertPublic(albert, xray)
        self.assertPublic(albert, yankee)
        self.assertPublic(albert, zulu)

        self.assertPublic(bob, bob)
        self.assertPublic(bob, yankee)

        self.assertPublic(charlie, charlie)
        self.assertPublic(charlie, zulu)

        self.assertPublic(doug, doug)


class PolicySimple(BranchVisibilityPolicyTestCase):
    """Test the visibility policy where the base visibility rule is PUBLIC
    with one team specified to have PRIVATE branches.
    """

    def setUp(self):
        BranchVisibilityPolicyTestCase.setUp(self)
        self.defineTeamPolicies((
            (None, BranchVisibilityRule.PUBLIC),
            (self.xray, BranchVisibilityRule.PRIVATE),
            ))

    def test_xray_branches_private(self):
        """Branches created in the xray namespace will be private."""
        self.assertPrivateSubscriber(self.albert, self.xray, None)

    def test_xray_member_branches_private(self):
        """Branches created by members of the Xray team in their own namespace
        will be private with the Xray team subscribed.
        """
        self.assertPrivateSubscriber(self.albert, self.albert, self.xray)

    def test_xray_member_other_namespace_public(self):
        """Branches created by members of the Xray team in other team
        namespaces are public.
        """
        self.assertPublic(self.albert, self.yankee)
        self.assertPublic(self.albert, self.zulu)

    def test_public_branches(self):
        """Branches created by users not in team Xray are created as public
        branches.
        """
        albert, bob, charlie, doug = self.people
        xray, yankee, zulu = self.teams

        self.assertPublic(bob, bob)
        self.assertPublic(bob, yankee)

        self.assertPublic(charlie, charlie)
        self.assertPublic(charlie, zulu)

        self.assertPublic(doug, doug)


class PolicyPrivateOnly(BranchVisibilityPolicyTestCase):
    """Test the visibility policy where the base visibility rule is PUBLIC
    with one team specified to have the PRIVATE_ONLY rule.

    PRIVATE_ONLY only stops the user from changing the branch from private to
    public and for branch creation behaves in the same maner as the PRIVATE
    policy.
    """

    def setUp(self):
        BranchVisibilityPolicyTestCase.setUp(self)
        self.defineTeamPolicies((
            (None, BranchVisibilityRule.PUBLIC),
            (self.xray, BranchVisibilityRule.PRIVATE_ONLY),
            ))

    def test_xray_branches_private(self):
        """Branches created in the xray namespace will be private."""
        self.assertPrivateSubscriber(self.albert, self.xray, None)

    def test_xray_member_branches_private(self):
        """Branches created by members of the Xray team in their own namespace
        will be private with the Xray team subscribed.
        """
        self.assertPrivateSubscriber(self.albert, self.albert, self.xray)

    def test_xray_member_other_namespace_public(self):
        """Branches created by members of the Xray team in other team
        namespaces are public.
        """
        self.assertPublic(self.albert, self.yankee)
        self.assertPublic(self.albert, self.zulu)

    def test_public_branches(self):
        """Branches created by users not in team Xray are created as public
        branches.
        """
        albert, bob, charlie, doug = self.people
        xray, yankee, zulu = self.teams

        self.assertPublic(bob, bob)
        self.assertPublic(bob, yankee)

        self.assertPublic(charlie, charlie)
        self.assertPublic(charlie, zulu)

        self.assertPublic(doug, doug)


class PolicyForbidden(BranchVisibilityPolicyTestCase):
    """Test the visibility policy where the base visibility rule is FORBIDDEN
    with one team specified to have the PRIVATE branches and another team
    specified to have PUBLIC branches.
    """

    def setUp(self):
        BranchVisibilityPolicyTestCase.setUp(self)
        self.defineTeamPolicies((
            (None, BranchVisibilityRule.FORBIDDEN),
            (self.xray, BranchVisibilityRule.PRIVATE),
            (self.yankee, BranchVisibilityRule.PUBLIC),
            ))

    def test_rule_for_branch_most_specific(self):
        """Since Albert is in both xray and yankee, the PRIVATE rule is
        returned in preference to the PUBLIC one.
        """
        self.assertBranchRule(
            self.albert, self.albert, BranchVisibilityRule.PRIVATE)

    def test_rule_for_branch_exact_defined(self):
        """Branches in the yankee namespace will return the PUBLIC rule as it
        is defined for the branch owner.
        """
        self.assertBranchRule(
            self.albert, self.yankee, BranchVisibilityRule.PUBLIC)

    def test_branch_creation_forbidden_non_members(self):
        """People who are not members of Xray or Yankee are not allowed to
        create branches.
        """
        self.assertPolicyCheckRaises(
            BranchCreationForbidden, self.charlie, self.charlie)
        self.assertPolicyCheckRaises(
            BranchCreationForbidden, self.charlie, self.zulu)

        self.assertPolicyCheckRaises(
            BranchCreationForbidden, self.doug, self.doug)

    def test_branch_creation_forbidden_other_namespace(self):
        """People who are members of Xray or Yankee are not allowed to
        create branches in a namespace of a team that is not a member
        of Xray or Yankee.
        """
        self.assertPolicyCheckRaises(
            BranchCreationForbidden, self.albert, self.zulu)

    def test_yankee_branches_public(self):
        """Branches in the yankee namespace are public."""
        self.assertPublic(self.bob, self.yankee)
        self.assertPublic(self.albert, self.yankee)

    def test_yankee_member_branches_public(self):
        """Branches created by a member of Yankee, who is not a member
        of Xray will be public.
        """
        self.assertPublic(self.bob, self.bob)

    def test_xray_branches_private(self):
        """Branches in the xray namespace will be private."""
        self.assertPrivateSubscriber(self.albert, self.xray, None)

    def test_xray_member_branches_private(self):
        """Branches created by Xray team members in their own namespace
        will be private, and subscribed to by the Xray team.
        """
        self.assertPrivateSubscriber(self.albert, self.albert, self.xray)


class PolicyTeamPrivateOverlap(BranchVisibilityPolicyTestCase):
    """Test the visibility policy where a user is a member of multiple teams
    with PRIVATE branches enabled.
    """

    def setUp(self):
        BranchVisibilityPolicyTestCase.setUp(self)
        self.defineTeamPolicies((
            (self.xray, BranchVisibilityRule.PRIVATE),
            (self.zulu, BranchVisibilityRule.PRIVATE),
            ))

    def test_public_branches_for_non_members(self):
        """Branches created by people who are not members of xray or zulu
        will be public branches.
        """
        self.assertPublic(self.bob, self.bob)
        self.assertPublic(self.bob, self.yankee)
        self.assertPublic(self.doug, self.doug)

    def test_public_branches_for_members_in_other_namespace(self):
        """If a member of xray or zulu creates a branch for a team that is
        not a member of xray or zulu, then the branch will be a public branch.
        """
        self.assertPublic(self.albert, self.yankee)

    def test_team_branches_private(self):
        """Branches created in the namespace of a team that has private
        branches specified are private.
        """
        self.assertPrivateSubscriber(self.charlie, self.zulu, None)
        self.assertPrivateSubscriber(self.albert, self.zulu, None)
        self.assertPrivateSubscriber(self.albert, self.xray, None)

    def test_one_membership_private_with_subscriber(self):
        """If the creator of the branch is a member of only one team that has
        private branches set up, then that team will be subscribed to any
        branches that the creator registers in their own namespace.
        """
        self.assertPrivateSubscriber(self.charlie, self.charlie, self.zulu)

    def test_two_memberships_private_no_subscriber(self):
        """If the creator of the branch is a member of two or more teams
        that have private branches enabled, then when a branch is created
        in their own namespace, there are no implicit subscribers.

        This is done as we cannot guess which team should have access
        to the private branch.
        """
        self.assertPrivateSubscriber(self.albert, self.albert, None)


class ComplexPolicyStructure(BranchVisibilityPolicyTestCase):
    """Test the visibility policy with a complex policy structure.

    The base visibility policy is set to FORBIDDEN, with both xray and yankee
    teams creating PRIVATE branches.  Members of zulu team create PUBLIC
    branches.

    Branch creation is forbidden to all people who are not a member of
    one of the teams: xray, yankee or zulu.  Members of zulu can create
    branches that are public.  Branches created by members of xray and
    yankee in the team namespace are private, and branches created in the
    namespace of the user are also created private.
    """

    def setUp(self):
        BranchVisibilityPolicyTestCase.setUp(self)
        self.defineTeamPolicies((
            (None, BranchVisibilityRule.FORBIDDEN),
            (self.xray, BranchVisibilityRule.PRIVATE),
            (self.yankee, BranchVisibilityRule.PRIVATE_ONLY),
            (self.zulu, BranchVisibilityRule.PUBLIC),
            ))

    def test_rule_for_branch_most_specific(self):
        """Since Albert is in both xray and yankee, the PRIVATE_ONLY rule is
        returned in preference to the PUBLIC or PRIVATE one.
        """
        self.assertBranchRule(
            self.albert, self.albert, BranchVisibilityRule.PRIVATE_ONLY)

    def test_rule_for_branch_exact_defined(self):
        """Branches in the zulu namespace will return the PUBLIC rule as it is
        defined for the branch owner.
        """
        self.assertBranchRule(
            self.albert, self.xray, BranchVisibilityRule.PRIVATE)
        self.assertBranchRule(
            self.albert, self.yankee, BranchVisibilityRule.PRIVATE_ONLY)
        self.assertBranchRule(
            self.albert, self.zulu, BranchVisibilityRule.PUBLIC)

    def test_non_membership_cannot_create_branches(self):
        """A user who is not a member of any specified team gets the
        base policy, which is in this case FORBIDDEN.
        """
        self.assertPolicyCheckRaises(
            BranchCreationForbidden, self.doug, self.doug)

    def test_zulu_branches_public(self):
        """Branches pushed to the zulu team namespace are public branches."""
        self.assertPublic(self.albert, self.zulu)
        self.assertPublic(self.charlie, self.zulu)

    def test_zulu_members_only_public(self):
        """A user who is a member of zulu, and not a member of a team that
        specifies private branch creation have public branches when created
        in the user's own namespace.
        """
        self.assertPublic(self.charlie, self.charlie)

    def test_xray_and_yankee_branches_private(self):
        """Branches that are created in the namespace of either xray or yankee
        are private branches.
        """
        self.assertPrivateSubscriber(self.albert, self.xray, None)
        self.assertPrivateSubscriber(self.albert, self.yankee, None)
        self.assertPrivateSubscriber(self.bob, self.yankee, None)

    def test_xray_member_private_with_subscription(self):
        """Branches created by a user who is a member of only one team that
        specifies private branches will have branches in the user's namespace
        created as private branches with the team subscribed to them.
        """
        self.assertPrivateSubscriber(self.bob, self.bob, self.yankee)

    def test_multiple_memberships_private(self):
        """If the user is a member of multiple teams that specify private
        branches, then this overrides PUBLIC policy that may apply.

        Any branch created in the user's own namespace will not have any
        implicit subscribers.
        """
        self.assertPrivateSubscriber(self.albert, self.albert, None)


class TeamsWithinTeamsPolicies(BranchVisibilityPolicyTestCase):
    """Test the visibility policy when teams within teams have different
    visibility rules.
    """

    def setUp(self):
        """Join up the teams so zulu is in yankee, and yankee is in xray."""
        BranchVisibilityPolicyTestCase.setUp(self)
        self.yankee.addMember(self.zulu, self.albert, force_team_add=True)
        self.xray.addMember(self.yankee, self.albert, force_team_add=True)
        self.defineTeamPolicies((
            (None, BranchVisibilityRule.FORBIDDEN),
            (self.xray, BranchVisibilityRule.PRIVATE),
            (self.yankee, BranchVisibilityRule.PUBLIC),
            (self.zulu, BranchVisibilityRule.PRIVATE),
            ))

    def test_team_memberships(self):
        albert, bob, charlie, doug = self.people
        xray, yankee, zulu = self.teams
        # Albert is a member of all three teams.
        self.failUnless(albert.inTeam(xray),
                        "Albert should be in team Xray team.")
        self.failUnless(albert.inTeam(yankee),
                        "Albert should be in the Yankee.")
        self.failUnless(albert.inTeam(zulu),
                        "Albert should be in Zulu team.")
        # Bob is a member of Yankee, and now Xray.
        self.failUnless(bob.inTeam(xray),
                        "Bob should now be in team Xray team.")
        self.failUnless(bob.inTeam(yankee),
                        "Bob should be in the Yankee team.")
        self.failIf(bob.inTeam(zulu),
                    "Bob should not be in the Zulu team.")
        # Charlie is a member of Zulu, and through Zulu a member
        # of Yankee, and through Yankee a member of Xray.
        self.failUnless(charlie.inTeam(xray),
                        "Charlie should now be in team Xray team.")
        self.failUnless(charlie.inTeam(yankee),
                        "Charlie should now be in the Yankee team.")
        self.failUnless(charlie.inTeam(zulu),
                        "Charlie should be in the Zulu team.")
        # Doug is not a member of any
        self.failIf(doug.inTeam(xray),
                    "Doug should not be in team Xray team.")
        self.failIf(doug.inTeam(yankee),
                    "Doug should not be in the Yankee team.")
        self.failIf(doug.inTeam(zulu),
                    "Doug should not be in the Zulu team.")

    def test_non_membership_cannot_create_branches(self):
        """A user who is not a member of any specified team gets the
        base policy, which is in this case FORBIDDEN.
        """
        self.assertPolicyCheckRaises(
            BranchCreationForbidden, self.doug, self.doug)

    def test_xray_and_zulu_branches_private_no_subscriber(self):
        """All branches created in the namespace of teams that specify
        private branches are private with no subscribers.
        """
        self.assertPrivateSubscriber(self.albert, self.xray, None)
        self.assertPrivateSubscriber(self.bob, self.xray, None)
        self.assertPrivateSubscriber(self.charlie, self.xray, None)

        self.assertPrivateSubscriber(self.albert, self.zulu, None)
        self.assertPrivateSubscriber(self.charlie, self.zulu, None)

    def test_yankee_branches_public(self):
        """All branches created in the namespace of teams that specify
        public branches are public.
        """
        self.assertPublic(self.albert, self.yankee)
        self.assertPublic(self.bob, self.yankee)
        self.assertPublic(self.charlie, self.yankee)

    def test_privacy_through_team_membership_of_private_team(self):
        """Policies that apply to team apply to people that are members
        indirectly in the same way as direct membership.
        """
        self.assertPrivateSubscriber(self.bob, self.bob, self.xray)

    def test_multiple_private_policies_through_indirect_membership(self):
        """If a person is a member of a team that specifies private branches,
        and that team is also a member either directly or indirectly of
        another team that specifies private branches, then when members of
        those teams create branches, those branches have no implicit
        subscribers.
        """
        self.assertPrivateSubscriber(self.albert, self.albert, None)
        self.assertPrivateSubscriber(self.charlie, self.charlie, None)


class JunkBranches(BranchVisibilityPolicyTestCase):
    """Branches are considered junk if they have no associated product.
    It is the product that has the branch visibility policy, so junk branches
    have no related visibility policy."""

    def setUp(self):
        """Override the product used for the visibility checks."""
        BranchVisibilityPolicyTestCase.setUp(self)
        # Override the product that is used in the check tests.
        self.product = None

    def test_junk_branches_public(self):
        """Branches created by anyone that has no product defined are created
        as public branches.
        """
        self.assertPublic(self.albert, self.albert)

    def test_team_junk_branches(self):
        """Team junk branches are allowed, and are public."""
        self.assertPublic(self.albert, self.xray)

    def test_no_create_junk_branch_for_other_user(self):
        """One user can't create +junk branches owned by another."""
        self.assertPolicyCheckRaises(
            BranchCreatorNotOwner, self.albert, self.doug)


class TestBranchNamespaceMoveBranch(TestCaseWithFactory):
    """Test the IBranchNamespace.moveBranch method.

    The edge cases of the validateMove are tested in the NamespaceMixin for
    each of the namespaces.
    """

    layer = DatabaseFunctionalLayer

    def assertNamespacesEqual(self, expected, result):
        """Assert that the namespaces refer to the same thing.

        The name of the namespace contains the user name and the context
        parts, so is the easiest thing to check.
        """
        self.assertEqual(expected.name, result.name)

    def test_move_to_same_namespace(self):
        # Moving to the same namespace is effectively a no-op.  No exceptions
        # about matching branch names should be raised.
        branch = self.factory.makeAnyBranch()
        namespace = branch.namespace
        namespace.moveBranch(branch, branch.owner)
        self.assertNamespacesEqual(namespace, branch.namespace)

    def test_name_clash_raises(self):
        # A name clash will raise an exception.
        branch = self.factory.makeAnyBranch(name="test")
        another = self.factory.makeAnyBranch(owner=branch.owner, name="test")
        namespace = another.namespace
        self.assertRaises(
            BranchExists, namespace.moveBranch, branch, branch.owner)

    def test_move_with_rename(self):
        # A name clash with 'rename_if_necessary' set to True will cause the
        # branch to be renamed instead of raising an error.
        branch = self.factory.makeAnyBranch(name="test")
        another = self.factory.makeAnyBranch(owner=branch.owner, name="test")
        namespace = another.namespace
        namespace.moveBranch(branch, branch.owner, rename_if_necessary=True)
        self.assertEqual("test-1", branch.name)
        self.assertNamespacesEqual(namespace, branch.namespace)

    def test_move_with_new_name(self):
        # A new name for the branch can be specified as part of the move.
        branch = self.factory.makeAnyBranch(name="test")
        another = self.factory.makeAnyBranch(owner=branch.owner, name="test")
        namespace = another.namespace
        namespace.moveBranch(branch, branch.owner, new_name="foo")
        self.assertEqual("foo", branch.name)
        self.assertNamespacesEqual(namespace, branch.namespace)

    def test_sets_branch_owner(self):
        # Moving to a new namespace may change the owner of the branch if the
        # owner of the namespace is different.
        branch = self.factory.makeAnyBranch(name="test")
        team = self.factory.makeTeam(branch.owner)
        product = self.factory.makeProduct()
        namespace = ProductNamespace(team, product)
        namespace.moveBranch(branch, branch.owner)
        self.assertEqual(team, branch.owner)
        # And for paranoia.
        self.assertNamespacesEqual(namespace, branch.namespace)
