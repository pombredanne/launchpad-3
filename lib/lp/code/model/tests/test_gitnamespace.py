# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `IGitNamespace` implementations."""

from zope.component import getUtility

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.code.errors import (
    GitDefaultConflict,
    GitRepositoryExists,
    )
from lp.code.interfaces.gitrepository import IGitRepositorySet
from lp.code.model.gitnamespace import ProjectGitNamespace
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class TestGitNamespaceMoveRepository(TestCaseWithFactory):
    """Test the IGitNamespace.moveRepository method."""

    layer = DatabaseFunctionalLayer

    def assertNamespacesEqual(self, expected, result):
        """Assert that the namespaces refer to the same thing.

        The name of the namespace contains the user name and the context
        parts, so is the easiest thing to check.
        """
        self.assertEqual(expected.name, result.name)

    def test_move_to_same_namespace(self):
        # Moving to the same namespace is effectively a no-op.  No
        # exceptions about matching repository names should be raised.
        repository = self.factory.makeGitRepository()
        namespace = repository.namespace
        namespace.moveRepository(repository, repository.owner)
        self.assertNamespacesEqual(namespace, repository.namespace)

    def test_name_clash_raises(self):
        # A name clash will raise an exception.
        repository = self.factory.makeGitRepository(name=u"test")
        another = self.factory.makeGitRepository(
            owner=repository.owner, name=u"test")
        namespace = another.namespace
        self.assertRaises(
            GitRepositoryExists, namespace.moveRepository,
            repository, repository.owner)

    def test_move_with_rename(self):
        # A name clash with 'rename_if_necessary' set to True will cause the
        # repository to be renamed instead of raising an error.
        repository = self.factory.makeGitRepository(name=u"test")
        another = self.factory.makeGitRepository(
            owner=repository.owner, name=u"test")
        namespace = another.namespace
        namespace.moveRepository(
            repository, repository.owner, rename_if_necessary=True)
        self.assertEqual("test-1", repository.name)
        self.assertNamespacesEqual(namespace, repository.namespace)

    def test_move_with_new_name(self):
        # A new name for the repository can be specified as part of the move.
        repository = self.factory.makeGitRepository(name=u"test")
        another = self.factory.makeGitRepository(
            owner=repository.owner, name=u"test")
        namespace = another.namespace
        namespace.moveRepository(repository, repository.owner, new_name=u"foo")
        self.assertEqual("foo", repository.name)
        self.assertNamespacesEqual(namespace, repository.namespace)

    def test_sets_repository_owner(self):
        # Moving to a new namespace may change the owner of the repository
        # if the owner of the namespace is different.
        repository = self.factory.makeGitRepository(name=u"test")
        team = self.factory.makeTeam(repository.owner)
        project = self.factory.makeProduct()
        namespace = ProjectGitNamespace(team, project)
        namespace.moveRepository(repository, repository.owner)
        self.assertEqual(team, repository.owner)
        # And for paranoia.
        self.assertNamespacesEqual(namespace, repository.namespace)

    def test_target_default_clash_raises(self):
        # A clash between target_default repositories will raise an exception.
        repository = self.factory.makeGitRepository()
        repository.setTargetDefault(True)
        another = self.factory.makeGitRepository()
        another.setTargetDefault(True)
        self.assertRaisesWithContent(
            GitDefaultConflict,
            "The default repository for '%s' is already set to %s." % (
                another.target.displayname, another.unique_name),
            another.namespace.moveRepository,
            repository, getUtility(ILaunchpadCelebrities).admin.teamowner)

    def test_owner_default_clash_raises(self):
        # A clash between owner_default repositories will raise an exception.
        repository = self.factory.makeGitRepository()
        repository.setOwnerDefault(True)
        another = self.factory.makeGitRepository()
        another.setOwnerDefault(True)
        self.assertRaisesWithContent(
            GitDefaultConflict,
            "%s's default repository for '%s' is already set to %s." % (
                another.owner.displayname, another.target.displayname,
                another.unique_name),
            another.namespace.moveRepository,
            repository, getUtility(ILaunchpadCelebrities).admin.teamowner)

    def test_preserves_target_default(self):
        # If there is no clash, target_default is preserved.
        repository = self.factory.makeGitRepository()
        repository.setTargetDefault(True)
        another = self.factory.makeGitRepository()
        namespace = another.namespace
        namespace.moveRepository(
            repository, getUtility(ILaunchpadCelebrities).admin.teamowner)
        self.assertNamespacesEqual(namespace, repository.namespace)
        repository_set = getUtility(IGitRepositorySet)
        self.assertEqual(
            repository, repository_set.getDefaultRepository(another.target))

    def test_preserves_owner_default(self):
        # If there is no clash, owner_default is preserved.
        repository = self.factory.makeGitRepository()
        repository.setOwnerDefault(True)
        another = self.factory.makeGitRepository()
        namespace = another.namespace
        namespace.moveRepository(
            repository, getUtility(ILaunchpadCelebrities).admin.teamowner)
        self.assertNamespacesEqual(namespace, repository.namespace)
        repository_set = getUtility(IGitRepositorySet)
        self.assertEqual(
            repository,
            repository_set.getDefaultRepositoryForOwner(
                another.owner, another.target))
