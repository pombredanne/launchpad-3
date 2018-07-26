# Copyright 2015-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the IGitLookup implementation."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from lazr.uri import URI
from zope.component import getUtility

from lp.code.errors import (
    InvalidNamespace,
    NoSuchGitRepository,
    )
from lp.code.interfaces.gitlookup import (
    IGitLookup,
    IGitTraverser,
    )
from lp.code.interfaces.gitrepository import IGitRepositorySet
from lp.registry.errors import NoSuchSourcePackageName
from lp.registry.interfaces.person import NoSuchPerson
from lp.registry.interfaces.product import (
    InvalidProductName,
    NoSuchProduct,
    )
from lp.services.config import config
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestGetByHostingPath(TestCaseWithFactory):
    """Test `IGitLookup.getByHostingPath`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestGetByHostingPath, self).setUp()
        self.lookup = getUtility(IGitLookup)

    def test_exists(self):
        repository = self.factory.makeGitRepository()
        self.assertEqual(
            repository,
            self.lookup.getByHostingPath(repository.getInternalPath()))

    def test_missing(self):
        self.assertIsNone(self.lookup.getByHostingPath("nonexistent"))


class TestGetByUniqueName(TestCaseWithFactory):
    """Tests for `IGitLookup.getByUniqueName`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestGetByUniqueName, self).setUp()
        self.lookup = getUtility(IGitLookup)

    def test_not_found(self):
        unused_name = self.factory.getUniqueString()
        self.assertIsNone(self.lookup.getByUniqueName(unused_name))

    def test_invalid_name(self):
        # repository:branch forms are not valid as repository unique names.
        # Provoke various failure modes depending on where the invalid
        # component occurs in the traversal.
        repository = self.factory.makeGitRepository()
        self.assertIsNone(self.lookup.getByUniqueName(
            repository.unique_name + ":branch-name"))
        with person_logged_in(repository.owner):
            getUtility(IGitRepositorySet).setDefaultRepositoryForOwner(
                repository.owner, repository.target, repository,
                repository.owner)
        self.assertIsNone(self.lookup.getByUniqueName(
            repository.shortened_path + ":branch-name"))
        with person_logged_in(repository.target.owner):
            getUtility(IGitRepositorySet).setDefaultRepository(
                repository.target, repository)
        self.assertIsNone(self.lookup.getByUniqueName(
            repository.shortened_path + ":branch-name"))

    def test_project(self):
        repository = self.factory.makeGitRepository()
        self.assertEqual(
            repository, self.lookup.getByUniqueName(repository.unique_name))
        self.assertIsNone(self.lookup.getByUniqueName(
            repository.unique_name + "-nonexistent"))

    def test_package(self):
        dsp = self.factory.makeDistributionSourcePackage()
        repository = self.factory.makeGitRepository(target=dsp)
        self.assertEqual(
            repository, self.lookup.getByUniqueName(repository.unique_name))
        self.assertIsNone(self.lookup.getByUniqueName(
            repository.unique_name + "-nonexistent"))

    def test_personal(self):
        owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(owner=owner, target=owner)
        self.assertEqual(
            repository, self.lookup.getByUniqueName(repository.unique_name))
        self.assertIsNone(self.lookup.getByUniqueName(
            repository.unique_name + "-nonexistent"))


class TestGetByPath(TestCaseWithFactory):
    """Test `IGitLookup.getByPath`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestGetByPath, self).setUp()
        self.lookup = getUtility(IGitLookup)

    def test_project(self):
        repository = self.factory.makeGitRepository()
        self.assertEqual(
            (repository, ""), self.lookup.getByPath(repository.unique_name))

    def test_project_default(self):
        repository = self.factory.makeGitRepository()
        with person_logged_in(repository.target.owner):
            getUtility(IGitRepositorySet).setDefaultRepository(
                repository.target, repository)
        self.assertEqual(
            (repository, ""), self.lookup.getByPath(repository.shortened_path))

    def test_package(self):
        dsp = self.factory.makeDistributionSourcePackage()
        repository = self.factory.makeGitRepository(target=dsp)
        self.assertEqual(
            (repository, ""), self.lookup.getByPath(repository.unique_name))

    def test_package_default(self):
        dsp = self.factory.makeDistributionSourcePackage()
        repository = self.factory.makeGitRepository(target=dsp)
        with person_logged_in(repository.target.distribution.owner):
            getUtility(IGitRepositorySet).setDefaultRepository(
                repository.target, repository)
        self.assertEqual(
            (repository, ""), self.lookup.getByPath(repository.shortened_path))

    def test_personal(self):
        owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(owner=owner, target=owner)
        self.assertEqual(
            (repository, ""), self.lookup.getByPath(repository.unique_name))

    def test_extra_path(self):
        repository = self.factory.makeGitRepository()
        self.assertEqual(
            (repository, "foo/bar"),
            self.lookup.getByPath("%s/foo/bar" % repository.unique_name))

    def test_default_extra_path(self):
        repository = self.factory.makeGitRepository()
        with person_logged_in(repository.target.owner):
            getUtility(IGitRepositorySet).setDefaultRepository(
                repository.target, repository)
        self.assertEqual(
            (repository, "foo/bar"),
            self.lookup.getByPath("%s/foo/bar" % repository.shortened_path))

    def test_invalid_namespace(self):
        # If `getByPath` is given a path to something with no default Git
        # repository, such as a distribution, it returns (None, _).
        distro = self.factory.makeDistribution()
        self.assertIsNone(self.lookup.getByPath(distro.name)[0])

    def test_no_default_git_repository(self):
        # If `getByPath` is given a path to something that could have a Git
        # repository but doesn't, it returns (None, _).
        project = self.factory.makeProduct()
        self.assertIsNone(self.lookup.getByPath(project.name)[0])

    def test_bare_person(self):
        # If `getByPath` is given a path to a person but nothing further, it
        # returns (None, _) even if the person exists.
        owner = self.factory.makePerson()
        self.assertIsNone(self.lookup.getByPath("~%s" % owner.name)[0])


class TestGetByUrl(TestCaseWithFactory):
    """Test `IGitLookup.getByUrl`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestGetByUrl, self).setUp()
        self.lookup = getUtility(IGitLookup)

    def makeProjectRepository(self):
        owner = self.factory.makePerson(name="aa")
        project = self.factory.makeProduct(name="bb")
        return self.factory.makeGitRepository(
            owner=owner, target=project, name="cc")

    def test_getByUrl_with_none(self):
        # getByUrl returns None if given None.
        self.assertIsNone(self.lookup.getByUrl(None))

    def assertUrlMatches(self, url, repository):
        self.assertEqual(repository, self.lookup.getByUrl(url))

    def test_getByUrl_with_trailing_slash(self):
        # Trailing slashes are stripped from the URL prior to searching.
        repository = self.makeProjectRepository()
        self.assertUrlMatches(
            "git://git.launchpad.dev/~aa/bb/+git/cc/", repository)

    def test_getByUrl_with_trailing_segments(self):
        # URLs with trailing segments beyond the repository are rejected.
        self.makeProjectRepository()
        self.assertIsNone(
            self.lookup.getByUrl("git://git.launchpad.dev/~aa/bb/+git/cc/foo"))

    def test_getByUrl_with_git(self):
        # getByUrl recognises LP repositories for git URLs.
        repository = self.makeProjectRepository()
        self.assertUrlMatches(
            "git://git.launchpad.dev/~aa/bb/+git/cc", repository)

    def test_getByUrl_with_git_ssh(self):
        # getByUrl recognises LP repositories for git+ssh URLs.
        repository = self.makeProjectRepository()
        self.assertUrlMatches(
            "git+ssh://git.launchpad.dev/~aa/bb/+git/cc", repository)

    def test_getByUrl_with_https(self):
        # getByUrl recognises LP repositories for https URLs.
        repository = self.makeProjectRepository()
        self.assertUrlMatches(
            "https://git.launchpad.dev/~aa/bb/+git/cc", repository)

    def test_getByUrl_with_ssh(self):
        # getByUrl recognises LP repositories for ssh URLs.
        repository = self.makeProjectRepository()
        self.assertUrlMatches(
            "ssh://git.launchpad.dev/~aa/bb/+git/cc", repository)

    def test_getByUrl_with_ftp(self):
        # getByUrl does not recognise LP repositories for ftp URLs.
        self.makeProjectRepository()
        self.assertIsNone(
            self.lookup.getByUrl("ftp://git.launchpad.dev/~aa/bb/+git/cc"))

    def test_getByUrl_with_lp(self):
        # getByUrl supports lp: URLs.
        url = "lp:~aa/bb/+git/cc"
        self.assertIsNone(self.lookup.getByUrl(url))
        repository = self.makeProjectRepository()
        self.assertUrlMatches(url, repository)

    def test_getByUrl_with_default(self):
        # getByUrl honours default repositories when looking up URLs.
        repository = self.makeProjectRepository()
        with person_logged_in(repository.target.owner):
            getUtility(IGitRepositorySet).setDefaultRepository(
                repository.target, repository)
        self.assertUrlMatches("lp:bb", repository)

    def test_uriToPath(self):
        # uriToPath only supports our own URLs with certain schemes.
        uri = URI(config.codehosting.git_anon_root)
        uri.path = "/~foo/bar/baz"
        # Test valid schemes.
        for scheme in ("git", "git+ssh", "https", "ssh"):
            uri.scheme = scheme
            self.assertEqual("~foo/bar/baz", self.lookup.uriToPath(uri))
        # Test an invalid scheme.
        uri.scheme = "ftp"
        self.assertIsNone(self.lookup.uriToPath(uri))
        # Test valid scheme but invalid domain.
        uri.scheme = 'sftp'
        uri.host = 'example.com'
        self.assertIsNone(self.lookup.uriToPath(uri))


class TestGitTraverser(TestCaseWithFactory):
    """Tests for the repository traverser."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestGitTraverser, self).setUp()
        self.traverser = getUtility(IGitTraverser)

    def assertTraverses(self, path, owner, target, repository=None):
        self.assertEqual(
            (owner, target, repository), self.traverser.traverse_path(path))

    def test_nonexistent_project(self):
        # `traverse_path` raises `NoSuchProduct` when resolving a path of
        # 'project' if the project doesn't exist.
        self.assertRaises(NoSuchProduct, self.traverser.traverse_path, "bb")

    def test_invalid_project(self):
        # `traverse_path` raises `InvalidProductName` when resolving a path
        # for a completely invalid default project repository.
        self.assertRaises(
            InvalidProductName, self.traverser.traverse_path, "b")

    def test_project(self):
        # `traverse_path` resolves the name of a project to the project itself.
        project = self.factory.makeProduct()
        self.assertTraverses(project.name, None, project)

    def test_project_no_named_repositories(self):
        # Projects do not have named repositories without an owner context,
        # so trying to traverse to them raises `InvalidNamespace`.
        project = self.factory.makeProduct()
        repository = self.factory.makeGitRepository(target=project)
        self.assertRaises(
            InvalidNamespace, self.traverser.traverse_path,
            "%s/+git/%s" % (project.name, repository.name))

    def test_no_such_distribution(self):
        # `traverse_path` raises `NoSuchProduct` if the distribution doesn't
        # exist.  That's because it can't tell the difference between the
        # name of a project that doesn't exist and the name of a
        # distribution that doesn't exist.
        self.assertRaises(
            NoSuchProduct, self.traverser.traverse_path,
            "distro/+source/package")

    def test_missing_sourcepackagename(self):
        # `traverse_path` raises `InvalidNamespace` if there are no segments
        # after '+source'.
        self.factory.makeDistribution(name="distro")
        self.assertRaises(
            InvalidNamespace, self.traverser.traverse_path, "distro/+source")

    def test_no_such_sourcepackagename(self):
        # `traverse_path` raises `NoSuchSourcePackageName` if the package in
        # distro/+source/package doesn't exist.
        self.factory.makeDistribution(name="distro")
        self.assertRaises(
            NoSuchSourcePackageName, self.traverser.traverse_path,
            "distro/+source/nonexistent")

    def test_package(self):
        # `traverse_path` resolves 'distro/+source/package' to the
        # distribution source package.
        dsp = self.factory.makeDistributionSourcePackage()
        path = "%s/+source/%s" % (
            dsp.distribution.name, dsp.sourcepackagename.name)
        self.assertTraverses(path, None, dsp)

    def test_package_no_named_repositories(self):
        # Packages do not have named repositories without an owner context,
        # so trying to traverse to them raises `InvalidNamespace`.
        dsp = self.factory.makeDistributionSourcePackage()
        repository = self.factory.makeGitRepository(target=dsp)
        self.assertRaises(
            InvalidNamespace, self.traverser.traverse_path,
            "%s/+source/%s/+git/%s" % (
                dsp.distribution.name, dsp.sourcepackagename.name,
                repository.name))

    def test_nonexistent_person(self):
        # `traverse_path` raises `NoSuchPerson` when resolving a path of
        # '~person/project' if the person doesn't exist.
        self.assertRaises(
            NoSuchPerson, self.traverser.traverse_path, "~person/bb")

    def test_nonexistent_person_project(self):
        # `traverse_path` raises `NoSuchProduct` when resolving a path of
        # '~person/project' if the project doesn't exist.
        self.factory.makePerson(name="person")
        self.assertRaises(
            NoSuchProduct, self.traverser.traverse_path, "~person/bb")

    def test_invalid_person_project(self):
        # `traverse_path` raises `InvalidProductName` when resolving a path
        # for a person and a completely invalid default project repository.
        self.factory.makePerson(name="person")
        self.assertRaises(
            InvalidProductName, self.traverser.traverse_path, "~person/b")

    def test_invalid_person_project_group(self):
        # Project groups do not have repositories, so `traverse_path` raises
        # `InvalidNamespace` when asked to traverse to them.
        person = self.factory.makePerson()
        project_group = self.factory.makeProject()
        self.assertRaises(
            InvalidNamespace, self.traverser.traverse_path,
            "~%s/%s/+git/repository" % (person.name, project_group.name))

    def test_person_missing_repository_name(self):
        # `traverse_path` raises `InvalidNamespace` if there are no segments
        # after '+git'.
        self.factory.makePerson(name="person")
        self.assertRaises(
            InvalidNamespace, self.traverser.traverse_path, "~person/+git")

    def test_person_no_such_repository(self):
        # `traverse_path` raises `NoSuchGitRepository` if the repository in
        # project/+git/repository doesn't exist.
        self.factory.makePerson(name="person")
        self.assertRaises(
            NoSuchGitRepository, self.traverser.traverse_path,
            "~person/+git/repository")

    def test_person_repository(self):
        # `traverse_path` resolves an existing project repository.
        person = self.factory.makePerson(name="person")
        repository = self.factory.makeGitRepository(
            owner=person, target=person, name="repository")
        self.assertTraverses(
            "~person/+git/repository", person, person, repository)

    def test_person_project(self):
        # `traverse_path` resolves '~person/project' to the person and the
        # project.
        person = self.factory.makePerson()
        project = self.factory.makeProduct()
        self.assertTraverses(
            "~%s/%s" % (person.name, project.name), person, project)

    def test_person_project_missing_repository_name(self):
        # `traverse_path` raises `InvalidNamespace` if there are no segments
        # after '+git'.
        person = self.factory.makePerson()
        project = self.factory.makeProduct()
        self.assertRaises(
            InvalidNamespace, self.traverser.traverse_path,
            "~%s/%s/+git" % (person.name, project.name))

    def test_person_project_no_such_repository(self):
        # `traverse_path` raises `NoSuchGitRepository` if the repository in
        # ~person/project/+git/repository doesn't exist.
        person = self.factory.makePerson()
        project = self.factory.makeProduct()
        self.assertRaises(
            NoSuchGitRepository, self.traverser.traverse_path,
            "~%s/%s/+git/nonexistent" % (person.name, project.name))

    def test_person_project_repository(self):
        # `traverse_path` resolves an existing person-project repository.
        person = self.factory.makePerson()
        project = self.factory.makeProduct()
        repository = self.factory.makeGitRepository(
            owner=person, target=project)
        self.assertTraverses(
            "~%s/%s/+git/%s" % (person.name, project.name, repository.name),
            person, project, repository)

    def test_no_such_person_distribution(self):
        # `traverse_path` raises `NoSuchProduct` when resolving a path of
        # '~person/distro' if the distribution doesn't exist.  That's
        # because it can't tell the difference between the name of a project
        # that doesn't exist and the name of a distribution that doesn't
        # exist.
        self.factory.makePerson(name="person")
        self.assertRaises(
            NoSuchProduct, self.traverser.traverse_path,
            "~person/distro/+source/package")

    def test_missing_person_sourcepackagename(self):
        # `traverse_path` raises `InvalidNamespace` if there are no segments
        # after '+source' in a person-DSP path.
        self.factory.makePerson(name="person")
        self.factory.makeDistribution(name="distro")
        self.assertRaises(
            InvalidNamespace, self.traverser.traverse_path,
            "~person/distro/+source")

    def test_no_such_person_sourcepackagename(self):
        # `traverse_path` raises `NoSuchSourcePackageName` if the package in
        # ~person/distro/+source/package doesn't exist.
        self.factory.makePerson(name="person")
        self.factory.makeDistribution(name="distro")
        self.assertRaises(
            NoSuchSourcePackageName, self.traverser.traverse_path,
            "~person/distro/+source/nonexistent")

    def test_person_package(self):
        # `traverse_path` resolves '~person/distro/+source/package' to the
        # person and the DSP.
        person = self.factory.makePerson()
        dsp = self.factory.makeDistributionSourcePackage()
        path = "~%s/%s/+source/%s" % (
            person.name, dsp.distribution.name, dsp.sourcepackagename.name)
        self.assertTraverses(path, person, dsp)

    def test_person_package_missing_repository_name(self):
        # `traverse_path` raises `InvalidNamespace` if there are no segments
        # after '+git'.
        person = self.factory.makePerson()
        dsp = self.factory.makeDistributionSourcePackage()
        self.assertRaises(
            InvalidNamespace, self.traverser.traverse_path,
            "~%s/%s/+source/%s/+git" % (
                person.name, dsp.distribution.name,
                dsp.sourcepackagename.name))

    def test_person_package_no_such_repository(self):
        # `traverse_path` raises `NoSuchGitRepository` if the repository in
        # ~person/project/+git/repository doesn't exist.
        person = self.factory.makePerson()
        dsp = self.factory.makeDistributionSourcePackage()
        self.assertRaises(
            NoSuchGitRepository, self.traverser.traverse_path,
            "~%s/%s/+source/%s/+git/nonexistent" % (
                person.name, dsp.distribution.name,
                dsp.sourcepackagename.name))

    def test_person_package_repository(self):
        # `traverse_path` resolves an existing person-package repository.
        person = self.factory.makePerson()
        dsp = self.factory.makeDistributionSourcePackage()
        repository = self.factory.makeGitRepository(owner=person, target=dsp)
        self.assertTraverses(
            "~%s/%s/+source/%s/+git/%s" % (
                person.name, dsp.distribution.name, dsp.sourcepackagename.name,
                repository.name),
            person, dsp, repository)

    def test_person_repository_from_person(self):
        # To save on queries, `traverse` can be given a person as a starting
        # point for the traversal.
        person = self.factory.makePerson(name="person")
        repository = self.factory.makeGitRepository(
            owner=person, target=person, name="repository")
        segments = ["~person", "+git", "repository"]
        self.assertEqual(
            (person, person, repository, None),
            self.traverser.traverse(iter(segments)))
        self.assertEqual(
            (person, person, repository, None),
            self.traverser.traverse(iter(segments[1:]), owner=person))
