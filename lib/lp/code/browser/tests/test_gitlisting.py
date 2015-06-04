# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for Git listing views."""

__metaclass__ = type

from BeautifulSoup import BeautifulSoup
from zope.component import getUtility

from lp.app.enums import InformationType
from lp.code.interfaces.gitrepository import IGitRepositorySet
from lp.registry.model.personproduct import PersonProduct
from lp.testing import (
    admin_logged_in,
    anonymous_logged_in,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.views import create_initialized_view


class TestTargetGitListingView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_rendering(self):
        owner = self.factory.makePerson(name=u"foowner")
        product = self.factory.makeProduct(name=u"foo", owner=owner)
        main_repo = self.factory.makeGitRepository(
            owner=owner, target=product, name=u"foo")
        self.factory.makeGitRefs(
            main_repo,
            paths=[u"refs/heads/master", u"refs/heads/1.0", u"refs/tags/1.1"])

        other_repo = self.factory.makeGitRepository(
            owner=self.factory.makePerson(name=u"contributor"),
            target=product, name=u"foo")
        self.factory.makeGitRefs(other_repo, paths=[u"refs/heads/bug-1234"])
        self.factory.makeGitRepository(
            owner=self.factory.makePerson(name=u"random"),
            target=product, name=u"bar")

        with admin_logged_in():
            getUtility(IGitRepositorySet).setDefaultRepository(
                target=product, repository=main_repo)
            getUtility(IGitRepositorySet).setDefaultRepositoryForOwner(
                owner=other_repo.owner, target=product, repository=other_repo,
                user=other_repo.owner)

        view = create_initialized_view(product, '+git')
        self.assertEqual(main_repo, view.default_git_repository)

        content = view()
        soup = BeautifulSoup(content)

        # Clone instructions for the default repo are present.
        self.assertEqual(
            'git://git.launchpad.dev/foo',
            soup.find(attrs={'class': 'anon-url'}).find(text=True))
        self.assertEqual(
            'https://git.launchpad.dev/~foowner/foo/+git/foo',
            soup.find(text='Browse the code').parent['href'])

        # The default repo's branches are shown, but not its tags.
        table = soup.find(
            'div', id='default-repository-branches').find('table')
        self.assertContentEqual(
            ['1.0', 'master'],
            [link.find(text=True) for link in table.findAll('a')])
        self.assertEndsWith(
            table.find(text="1.0").parent['href'],
            u"/~foowner/foo/+git/foo/+ref/1.0")

        # Other repos are listed.
        table = soup.find(
            'div', id='gitrepositories-table-listing').find('table')
        self.assertContentEqual(
            ['lp:foo', 'lp:~random/foo/+git/bar', 'lp:~contributor/foo'],
            [link.find(text=True) for link in table.findAll('a')])
        self.assertEndsWith(
            table.find(text="lp:~contributor/foo").parent['href'],
            u"/~contributor/foo/+git/foo")

        # But not their branches.
        self.assertNotIn('bug-1234', content)

    def test_copes_with_no_default(self):
        owner = self.factory.makePerson(name=u"foowner")
        product = self.factory.makeProduct(name=u"foo", owner=owner)

        self.factory.makeGitRepository(
            owner=self.factory.makePerson(name=u"contributor"),
            target=product, name=u"foo")

        view = create_initialized_view(product, '+git')
        self.assertIs(None, view.default_git_repository)

        content = view()
        soup = BeautifulSoup(content)

        # No details about the non-existent default repo are shown.
        # XXX: This should show instructions to create one.
        self.assertNotIn('Branches', content)
        self.assertNotIn('Browse the code', content)
        self.assertNotIn('git clone', content)

        # Other repos are listed.
        table = soup.find(
            'div', id='gitrepositories-table-listing').find('table')
        self.assertContentEqual(
            ['lp:~contributor/foo/+git/foo'],
            [link.find(text=True) for link in table.findAll('a')])

    def test_copes_with_private_repos(self):
        product = self.factory.makeProduct()
        invisible_repo = self.factory.makeGitRepository(
            target=product, information_type=InformationType.PRIVATESECURITY)
        other_repo = self.factory.makeGitRepository(
            target=product, information_type=InformationType.PUBLIC)
        with admin_logged_in():
            getUtility(IGitRepositorySet).setDefaultRepository(
                target=product, repository=invisible_repo)

        # An anonymous user can't see the default.
        with anonymous_logged_in():
            anon_view = create_initialized_view(product, '+git')
            self.assertIs(None, anon_view.default_git_repository)
            self.assertContentEqual(
                [other_repo], anon_view.repo_collection.getRepositories())

        # Neither can a random unprivileged user.
        with person_logged_in(self.factory.makePerson()):
            anon_view = create_initialized_view(product, '+git')
            self.assertIs(None, anon_view.default_git_repository)
            self.assertContentEqual(
                [other_repo], anon_view.repo_collection.getRepositories())

        # But someone who can see the repo gets the normal view.
        with person_logged_in(product.owner):
            owner_view = create_initialized_view(
                product, '+git', user=product.owner)
            self.assertEqual(invisible_repo, owner_view.default_git_repository)
            self.assertContentEqual(
                [invisible_repo, other_repo],
                owner_view.repo_collection.getRepositories())

    def test_bzr_link(self):
        product = self.factory.makeProduct()

        # With a fresh product there's no Bazaar link.
        view = create_initialized_view(product, '+git')
        self.assertNotIn('View Bazaar branches', view())

        # But it appears once we create a branch.
        self.factory.makeBranch(product=product)
        view = create_initialized_view(product, '+git')
        self.assertIn('View Bazaar branches', view())


class TestPersonTargetGitListingView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_rendering(self):
        owner = self.factory.makePerson(name=u"dev")
        product = self.factory.makeProduct(name=u"foo")
        default_repo = self.factory.makeGitRepository(
            owner=owner, target=product, name=u"foo")
        self.factory.makeGitRefs(
            default_repo,
            paths=[u"refs/heads/master", u"refs/heads/bug-1234"])

        other_repo = self.factory.makeGitRepository(
            owner=owner, target=product, name=u"bar")
        self.factory.makeGitRefs(other_repo, paths=[u"refs/heads/bug-2468"])

        with admin_logged_in():
            getUtility(IGitRepositorySet).setDefaultRepositoryForOwner(
                owner=owner, target=product, repository=default_repo,
                user=owner)

        view = create_initialized_view(PersonProduct(owner, product), '+git')
        self.assertEqual(default_repo, view.default_git_repository)

        content = view()
        soup = BeautifulSoup(content)

        # Clone instructions for the default repo are present.
        self.assertEqual(
            'git://git.launchpad.dev/~dev/foo',
            soup.find(attrs={'class': 'anon-url'}).find(text=True))
        self.assertEqual(
            'https://git.launchpad.dev/~dev/foo/+git/foo',
            soup.find(text='Browse the code').parent['href'])

        # The default repo's branches are shown.
        table = soup.find(
            'div', id='default-repository-branches').find('table')
        self.assertContentEqual(
            ['master', 'bug-1234'],
            [link.find(text=True) for link in table.findAll('a')])
        self.assertEndsWith(
            table.find(text="bug-1234").parent['href'],
            u"/~dev/foo/+git/foo/+ref/bug-1234")

        # Other repos are listed.
        table = soup.find(
            'div', id='gitrepositories-table-listing').find('table')
        self.assertContentEqual(
            ['lp:~dev/foo', 'lp:~dev/foo/+git/bar'],
            [link.find(text=True) for link in table.findAll('a')])
        self.assertEndsWith(
            table.find(text="lp:~dev/foo/+git/bar").parent['href'],
            u"/~dev/foo/+git/bar")

        # But not their branches.
        self.assertNotIn('bug-2468', content)

    def test_copes_with_no_default(self):
        owner = self.factory.makePerson(name=u"dev")
        product = self.factory.makeProduct(name=u"foo", owner=owner)

        self.factory.makeGitRepository(
            owner=owner, target=product, name=u"foo")

        view = create_initialized_view(PersonProduct(owner, product), '+git')
        self.assertIs(None, view.default_git_repository)

        content = view()
        soup = BeautifulSoup(content)

        # No details about the non-existent default repo are shown.
        # XXX: This should show instructions to create one.
        self.assertNotIn('Branches', content)
        self.assertNotIn('Browse the code', content)
        self.assertNotIn('git clone', content)

        # Other repos are listed.
        table = soup.find(
            'div', id='gitrepositories-table-listing').find('table')
        self.assertContentEqual(
            ['lp:~dev/foo/+git/foo'],
            [link.find(text=True) for link in table.findAll('a')])

    def test_copes_with_private_repos(self):
        owner = self.factory.makePerson(name=u"dev")
        product = self.factory.makeProduct()
        invisible_repo = self.factory.makeGitRepository(
            owner=owner, target=product,
            information_type=InformationType.PRIVATESECURITY)
        other_repo = self.factory.makeGitRepository(
            owner=owner, target=product,
            information_type=InformationType.PUBLIC)
        with admin_logged_in():
            getUtility(IGitRepositorySet).setDefaultRepositoryForOwner(
                owner=owner, target=product, repository=invisible_repo,
                user=owner)

        pp = PersonProduct(owner, product)

        # An anonymous user can't see the default.
        with anonymous_logged_in():
            anon_view = create_initialized_view(pp, '+git')
            self.assertIs(None, anon_view.default_git_repository)
            self.assertContentEqual(
                [other_repo], anon_view.repo_collection.getRepositories())

        # Neither can a random unprivileged user.
        with person_logged_in(self.factory.makePerson()):
            anon_view = create_initialized_view(pp, '+git')
            self.assertIs(None, anon_view.default_git_repository)
            self.assertContentEqual(
                [other_repo], anon_view.repo_collection.getRepositories())

        # But someone who can see the repo gets the normal view.
        with person_logged_in(owner):
            owner_view = create_initialized_view(pp, '+git', user=owner)
            self.assertEqual(invisible_repo, owner_view.default_git_repository)
            self.assertContentEqual(
                [invisible_repo, other_repo],
                owner_view.repo_collection.getRepositories())

    def test_bzr_link(self):
        owner = self.factory.makePerson()
        product = self.factory.makeProduct()
        pp = PersonProduct(owner, product)

        # With a fresh product there's no Bazaar link.
        view = create_initialized_view(pp, '+git')
        self.assertNotIn('View Bazaar branches', view())

        # But it appears once we create a branch.
        self.factory.makeBranch(owner=owner, product=product)
        view = create_initialized_view(pp, '+git')
        self.assertIn('View Bazaar branches', view())
