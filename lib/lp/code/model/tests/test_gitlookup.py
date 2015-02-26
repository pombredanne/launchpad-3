# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the IGitLookup implementation."""

__metaclass__ = type

from lazr.uri import URI
from zope.component import getUtility

from lp.code.errors import InvalidNamespace
from lp.code.interfaces.gitlookup import (
    IDefaultGitTraverser,
    IGitLookup,
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


class TestGetByUniqueName(TestCaseWithFactory):
    """Tests for `IGitLookup.getByUniqueName`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestGetByUniqueName, self).setUp()
        self.lookup = getUtility(IGitLookup)

    def test_not_found(self):
        unused_name = self.factory.getUniqueString()
        self.assertIsNone(self.lookup.getByUniqueName(unused_name))

    def test_project(self):
        repository = self.factory.makeGitRepository()
        self.assertEqual(
            repository, self.lookup.getByUniqueName(repository.unique_name))

    def test_package(self):
        dsp = self.factory.makeDistributionSourcePackage()
        repository = self.factory.makeGitRepository(target=dsp)
        self.assertEqual(
            repository, self.lookup.getByUniqueName(repository.unique_name))

    def test_personal(self):
        owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(owner=owner, target=owner)
        self.assertEqual(
            repository, self.lookup.getByUniqueName(repository.unique_name))


class TestGetByPath(TestCaseWithFactory):
    """Test `IGitLookup.getByPath`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestGetByPath, self).setUp()
        self.lookup = getUtility(IGitLookup)

    def test_project(self):
        repository = self.factory.makeGitRepository()
        self.assertEqual(
            repository, self.lookup.getByPath(repository.unique_name))

    def test_project_default(self):
        repository = self.factory.makeGitRepository()
        with person_logged_in(repository.target.owner):
            getUtility(IGitRepositorySet).setDefaultRepository(
                repository.target, repository)
        self.assertEqual(
            repository, self.lookup.getByPath(repository.shortened_path))

    def test_package(self):
        dsp = self.factory.makeDistributionSourcePackage()
        repository = self.factory.makeGitRepository(target=dsp)
        self.assertEqual(
            repository, self.lookup.getByPath(repository.unique_name))

    def test_package_default(self):
        dsp = self.factory.makeDistributionSourcePackage()
        repository = self.factory.makeGitRepository(target=dsp)
        with person_logged_in(repository.target.distribution.owner):
            getUtility(IGitRepositorySet).setDefaultRepository(
                repository.target, repository)
        self.assertEqual(
            repository, self.lookup.getByPath(repository.shortened_path))

    def test_personal(self):
        owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(owner=owner, target=owner)
        self.assertEqual(
            repository, self.lookup.getByPath(repository.unique_name))

    def test_invalid_namespace(self):
        # If `getByPath` is given a path to something with no default Git
        # repository, such as a distribution, it raises InvalidNamespace.
        distro = self.factory.makeDistribution()
        self.assertRaises(InvalidNamespace, self.lookup.getByPath, distro.name)

    def test_no_default_git_repository(self):
        # If `getByPath` is given a path to something that could have a Git
        # repository but doesn't, it returns None.
        project = self.factory.makeProduct()
        self.assertIsNone(self.lookup.getByPath(project.name))


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
            owner=owner, target=project, name=u"cc")

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

    def test_uriToHostingPath(self):
        # uriToHostingPath only supports our own URLs with certain schemes.
        uri = URI(config.codehosting.git_anon_root)
        uri.path = "/~foo/bar/baz"
        # Test valid schemes.
        for scheme in ("git", "git+ssh", "https", "ssh"):
            uri.scheme = scheme
            self.assertEqual("~foo/bar/baz", self.lookup.uriToHostingPath(uri))
        # Test an invalid scheme.
        uri.scheme = "ftp"
        self.assertIsNone(self.lookup.uriToHostingPath(uri))
        # Test valid scheme but invalid domain.
        uri.scheme = 'sftp'
        uri.host = 'example.com'
        self.assertIsNone(self.lookup.uriToHostingPath(uri))


class TestDefaultGitTraverser(TestCaseWithFactory):
    """Tests for the default repository traverser."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestDefaultGitTraverser, self).setUp()
        self.traverser = getUtility(IDefaultGitTraverser)

    def assertTraverses(self, path, owner, target):
        self.assertEqual((owner, target), self.traverser.traverse(path))

    def test_nonexistent_project(self):
        # `traverse` raises `NoSuchProduct` when resolving a path of
        # 'project' if the project doesn't exist.
        self.assertRaises(NoSuchProduct, self.traverser.traverse, "bb")

    def test_invalid_project(self):
        # `traverse` raises `InvalidProductName` when resolving a path for a
        # completely invalid default project repository.
        self.assertRaises(InvalidProductName, self.traverser.traverse, "b")

    def test_project(self):
        # `traverse` resolves the name of a project to the project itself.
        project = self.factory.makeProduct()
        self.assertTraverses(project.name, None, project)

    def test_no_such_distribution(self):
        # `traverse` raises `NoSuchProduct` if the distribution doesn't
        # exist.  That's because it can't tell the difference between the
        # name of a project that doesn't exist and the name of a
        # distribution that doesn't exist.
        self.assertRaises(
            NoSuchProduct, self.traverser.traverse, "distro/+source/package")

    def test_missing_sourcepackagename(self):
        # `traverse` raises `InvalidNamespace` if there are no segments
        # after '+source'.
        self.factory.makeDistribution(name="distro")
        self.assertRaises(
            InvalidNamespace, self.traverser.traverse, "distro/+source")

    def test_no_such_sourcepackagename(self):
        # `traverse` raises `NoSuchSourcePackageName` if the package in
        # distro/+source/package doesn't exist.
        self.factory.makeDistribution(name="distro")
        self.assertRaises(
            NoSuchSourcePackageName, self.traverser.traverse,
            "distro/+source/nonexistent")

    def test_package(self):
        # `traverse` resolves 'distro/+source/package' to the distribution
        # source package.
        dsp = self.factory.makeDistributionSourcePackage()
        path = "%s/+source/%s" % (
            dsp.distribution.name, dsp.sourcepackagename.name)
        self.assertTraverses(path, None, dsp)

    def test_nonexistent_person(self):
        # `traverse` raises `NoSuchPerson` when resolving a path of
        # '~person/project' if the person doesn't exist.
        self.assertRaises(NoSuchPerson, self.traverser.traverse, "~person/bb")

    def test_nonexistent_person_project(self):
        # `traverse` raises `NoSuchProduct` when resolving a path of
        # '~person/project' if the project doesn't exist.
        self.factory.makePerson(name="person")
        self.assertRaises(NoSuchProduct, self.traverser.traverse, "~person/bb")

    def test_invalid_person_project(self):
        # `traverse` raises `InvalidProductName` when resolving a path for a
        # person and a completely invalid default project repository.
        self.factory.makePerson(name="person")
        self.assertRaises(
            InvalidProductName, self.traverser.traverse, "~person/b")

    def test_person_project(self):
        # `traverse` resolves '~person/project' to the person and the project.
        person = self.factory.makePerson()
        project = self.factory.makeProduct()
        self.assertTraverses(
            "~%s/%s" % (person.name, project.name), person, project)

    def test_no_such_person_distribution(self):
        # `traverse` raises `NoSuchProduct` when resolving a path of
        # '~person/distro' if the distribution doesn't exist.  That's
        # because it can't tell the difference between the name of a project
        # that doesn't exist and the name of a distribution that doesn't
        # exist.
        self.factory.makePerson(name="person")
        self.assertRaises(
            NoSuchProduct, self.traverser.traverse,
            "~person/distro/+source/package")

    def test_missing_person_sourcepackagename(self):
        # `traverse` raises `InvalidNamespace` if there are no segments
        # after '+source' in a person-DSP path.
        self.factory.makePerson(name="person")
        self.factory.makeDistribution(name="distro")
        self.assertRaises(
            InvalidNamespace, self.traverser.traverse,
            "~person/distro/+source")

    def test_no_such_person_sourcepackagename(self):
        # `traverse` raises `NoSuchSourcePackageName` if the package in
        # ~person/distro/+source/package doesn't exist.
        self.factory.makePerson(name="person")
        self.factory.makeDistribution(name="distro")
        self.assertRaises(
            NoSuchSourcePackageName, self.traverser.traverse,
            "~person/distro/+source/nonexistent")

    def test_person_package(self):
        # `traverse` resolves '~person/distro/+source/package' to the person
        # and the DSP.
        person = self.factory.makePerson()
        dsp = self.factory.makeDistributionSourcePackage()
        path = "~%s/%s/+source/%s" % (
            person.name, dsp.distribution.name, dsp.sourcepackagename.name)
        self.assertTraverses(path, person, dsp)
