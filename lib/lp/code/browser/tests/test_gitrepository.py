# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for GitRepositoryView."""

__metaclass__ = type

from BeautifulSoup import BeautifulSoup
from bzrlib import urlutils
from fixtures import FakeLogger
from zope.component import getUtility
from zope.publisher.interfaces import NotFound

from lp.app.enums import InformationType
from lp.app.interfaces.services import IService
from lp.code.interfaces.gitrepository import GIT_FEATURE_FLAG
from lp.registry.interfaces.person import PersonVisibility
from lp.services.config import config
from lp.services.features.testing import FeatureFixture
from lp.services.webapp.publisher import canonical_url
from lp.testing import (
    admin_logged_in,
    BrowserTestCase,
    login_person,
    logout,
    person_logged_in,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.pages import (
    setupBrowser,
    setupBrowserForUser,
    )
from lp.testing.views import create_initialized_view


class TestGitRepositoryView(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestGitRepositoryView, self).setUp()
        self.useFixture(FeatureFixture({GIT_FEATURE_FLAG: u"on"}))

    def test_anon_url_for_public(self):
        # Public repositories have an anonymous URL, visible to anyone.
        repository = self.factory.makeGitRepository()
        view = create_initialized_view(repository, "+index")
        expected_url = urlutils.join(
            config.codehosting.git_anon_root, repository.shortened_path)
        self.assertEqual(expected_url, view.anon_url)

    def test_anon_url_not_for_private(self):
        # Private repositories do not have an anonymous URL.
        owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(
            owner=owner, information_type=InformationType.USERDATA)
        with person_logged_in(owner):
            view = create_initialized_view(repository, "+index")
            self.assertIsNone(view.anon_url)

    def test_ssh_url_for_public_logged_in(self):
        # Public repositories have an SSH URL, visible if logged in.
        repository = self.factory.makeGitRepository()
        with person_logged_in(repository.owner):
            view = create_initialized_view(repository, "+index")
            expected_url = urlutils.join(
                config.codehosting.git_ssh_root, repository.shortened_path)
            self.assertEqual(expected_url, view.ssh_url)

    def test_ssh_url_for_public_not_anonymous(self):
        # Public repositories do not have an SSH URL if not logged in.
        repository = self.factory.makeGitRepository()
        view = create_initialized_view(repository, "+index")
        self.assertIsNone(view.ssh_url)

    def test_ssh_url_for_private(self):
        # Private repositories have an SSH URL.
        owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(
            owner=owner, information_type=InformationType.USERDATA)
        with person_logged_in(owner):
            view = create_initialized_view(repository, "+index")
            expected_url = urlutils.join(
                config.codehosting.git_ssh_root, repository.shortened_path)
            self.assertEqual(expected_url, view.ssh_url)

    def test_user_can_push(self):
        # A user can push if they have edit permissions.
        repository = self.factory.makeGitRepository()
        with person_logged_in(repository.owner):
            view = create_initialized_view(repository, "+index")
            self.assertTrue(view.user_can_push)

    def test_user_can_push_admins_can(self):
        # Admins can push to any repository.
        repository = self.factory.makeGitRepository()
        with admin_logged_in():
            view = create_initialized_view(repository, "+index")
            self.assertTrue(view.user_can_push)

    def test_user_can_push_non_owner(self):
        # Someone not associated with the repository cannot upload.
        repository = self.factory.makeGitRepository()
        with person_logged_in(self.factory.makePerson()):
            view = create_initialized_view(repository, "+index")
            self.assertFalse(view.user_can_push)

    def test_view_for_user_with_artifact_grant(self):
        # Users with an artifact grant for a repository related to a private
        # project can view the main repository page.
        owner = self.factory.makePerson()
        user = self.factory.makePerson()
        project = self.factory.makeProduct(
            owner=owner, information_type=InformationType.PROPRIETARY)
        with person_logged_in(owner):
            project_name = project.name
            repository = self.factory.makeGitRepository(
                owner=owner, target=project,
                information_type=InformationType.PROPRIETARY)
            getUtility(IService, "sharing").ensureAccessGrants(
                [user], owner, gitrepositories=[repository])
        with person_logged_in(user):
            url = canonical_url(repository)
        # The main check: No Unauthorized error should be raised.
        browser = self.getUserBrowser(url, user=user)
        self.assertIn(project_name, browser.contents)


class TestGitRepositoryViewPrivateArtifacts(BrowserTestCase):
    """ Tests that Git repositories with private team artifacts can be viewed.

    A repository may be associated with a private team as follows:
    - the owner is a private team

    A logged in user who is not authorised to see the private team(s) still
    needs to be able to view the repository.  The private team will be
    rendered in the normal way, displaying the team name and Launchpad URL.
    """

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestGitRepositoryViewPrivateArtifacts, self).setUp()
        self.useFixture(FeatureFixture({GIT_FEATURE_FLAG: u"on"}))

    def _getBrowser(self, user=None):
        if user is None:
            browser = setupBrowser()
            logout()
            return browser
        else:
            login_person(user)
            return setupBrowserForUser(user=user)

    def test_view_repository_with_private_owner(self):
        # A repository with a private owner is rendered.
        private_owner = self.factory.makeTeam(
            displayname="PrivateTeam", visibility=PersonVisibility.PRIVATE)
        with person_logged_in(private_owner):
            repository = self.factory.makeGitRepository(owner=private_owner)
        # Ensure the repository owner is rendered.
        url = canonical_url(repository, rootsite="code")
        user = self.factory.makePerson()
        browser = self._getBrowser(user)
        browser.open(url)
        soup = BeautifulSoup(browser.contents)
        self.assertIsNotNone(soup.find('a', text="PrivateTeam"))

    def test_anonymous_view_repository_with_private_owner(self):
        # A repository with a private owner is not rendered for anon users.
        self.useFixture(FakeLogger())
        private_owner = self.factory.makeTeam(
            visibility=PersonVisibility.PRIVATE)
        with person_logged_in(private_owner):
            repository = self.factory.makeGitRepository(owner=private_owner)
        # Viewing the branch results in an error.
        url = canonical_url(repository, rootsite="code")
        browser = self._getBrowser()
        self.assertRaises(NotFound, browser.open, url)
