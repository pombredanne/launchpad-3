# Copyright 2015-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for GitRepositoryView."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

import base64
from datetime import datetime
import doctest
from operator import attrgetter
import re
from textwrap import dedent

from fixtures import FakeLogger
import pytz
import soupmatchers
from storm.store import Store
from testtools.matchers import (
    AfterPreprocessing,
    DocTestMatches,
    Equals,
    Is,
    MatchesDict,
    MatchesListwise,
    MatchesSetwise,
    MatchesStructure,
    )
import transaction
from zope.component import getUtility
from zope.formlib.itemswidgets import ItemDisplayWidget
from zope.publisher.interfaces import NotFound
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from lp.app.enums import InformationType
from lp.app.errors import UnexpectedFormData
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.app.interfaces.services import IService
from lp.code.browser.gitrepository import encode_form_field_id
from lp.code.enums import (
    BranchMergeProposalStatus,
    CodeReviewVote,
    GitActivityType,
    GitGranteeType,
    GitPermissionType,
    GitRepositoryType,
    )
from lp.code.interfaces.revision import IRevisionSet
from lp.code.tests.helpers import GitHostingFixture
from lp.registry.enums import (
    BranchSharingPolicy,
    VCSType,
    )
from lp.registry.interfaces.accesspolicy import IAccessPolicySource
from lp.registry.interfaces.person import (
    IPerson,
    PersonVisibility,
    )
from lp.services.beautifulsoup import BeautifulSoup
from lp.services.database.constants import UTC_NOW
from lp.services.features.testing import FeatureFixture
from lp.services.webapp.publisher import canonical_url
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.testing import (
    admin_logged_in,
    BrowserTestCase,
    login_person,
    logout,
    person_logged_in,
    record_two_runs,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing.matchers import (
    Contains,
    HasQueryCount,
    )
from lp.testing.pages import (
    extract_text,
    find_tag_by_id,
    get_feedback_messages,
    setupBrowser,
    setupBrowserForUser,
    )
from lp.testing.publication import test_traverse
from lp.testing.views import (
    create_initialized_view,
    create_view,
    )


class TestGitRepositoryNavigation(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_traverse_ref(self):
        [ref] = self.factory.makeGitRefs()
        url = "%s/+ref/%s" % (canonical_url(ref.repository), ref.path)
        self.assertEqual(ref, test_traverse(url)[0])

    def test_traverse_ref_missing(self):
        repository = self.factory.makeGitRepository()
        url = "%s/+ref/refs/heads/master" % canonical_url(repository)
        self.assertRaises(NotFound, test_traverse, url)

    def test_traverse_quoted_ref(self):
        [ref] = self.factory.makeGitRefs(paths=["refs/heads/with#hash"])
        url = "%s/+ref/with%%23hash" % canonical_url(ref.repository)
        self.assertEqual(ref, test_traverse(url)[0])

    def test_traverse_non_ascii(self):
        [ref] = self.factory.makeGitRefs(paths=["refs/heads/\N{SNOWMAN}"])
        url = "%s/+ref/%%E2%%98%%83" % canonical_url(ref.repository)
        self.assertEqual(ref, test_traverse(url)[0])


class TestGitRepositoryView(BrowserTestCase):

    layer = LaunchpadFunctionalLayer

    def test_clone_instructions(self):
        repository = self.factory.makeGitRepository()
        username = repository.owner.name
        text = self.getMainText(repository, "+index", user=repository.owner)
        self.assertTextMatchesExpressionIgnoreWhitespace(r"""
            git clone https://git.launchpad.dev/.*
            git clone git\+ssh://{username}@git.launchpad.dev/.*
            """.format(username=username), text)

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
        # Someone not associated with the repository cannot push.
        repository = self.factory.makeGitRepository()
        with person_logged_in(self.factory.makePerson()):
            view = create_initialized_view(repository, "+index")
            self.assertFalse(view.user_can_push)

    def test_user_can_push_imported(self):
        # Even the owner of an imported repository cannot push.
        repository = self.factory.makeGitRepository(
            repository_type=GitRepositoryType.IMPORTED)
        with person_logged_in(repository.owner):
            view = create_initialized_view(repository, "+index")
            self.assertFalse(view.user_can_push)

    def test_push_directions_not_logged_in_individual(self):
        # If the user is not logged in, they are given appropriate
        # directions for a repository owned by a person.
        repository = self.factory.makeGitRepository()
        browser = self.getViewBrowser(repository, no_login=True)
        directions = find_tag_by_id(browser.contents, "push-directions")
        login_person(self.user)
        self.assertThat(directions.renderContents(), DocTestMatches(dedent("""
            Only <a
            href="http://launchpad.dev/~{owner.name}">{owner.display_name}</a>
            can upload to this repository. If you are {owner.display_name}
            please <a href="+login">log in</a> for upload directions.
            """).format(owner=repository.owner),
            flags=doctest.NORMALIZE_WHITESPACE))

    def test_push_directions_not_logged_in_team(self):
        # If the user is not logged in, they are given appropriate
        # directions for a repository owned by a team.
        team = self.factory.makeTeam()
        repository = self.factory.makeGitRepository(owner=team)
        browser = self.getViewBrowser(repository, no_login=True)
        directions = find_tag_by_id(browser.contents, "push-directions")
        login_person(self.user)
        self.assertThat(directions.renderContents(), DocTestMatches(dedent("""
            Members of <a
            href="http://launchpad.dev/~{owner.name}">{owner.display_name}</a>
            can upload to this repository. <a href="+login">Log in</a> for
            directions.
            """).format(owner=repository.owner),
            flags=doctest.NORMALIZE_WHITESPACE))

    def test_push_directions_logged_in_can_push(self):
        # If the user is logged in and can push to the repository, we
        # explain how to do so.
        self.factory.makeSSHKey(person=self.user, send_notification=False)
        repository = self.factory.makeGitRepository(owner=self.user)
        username = self.user.name
        browser = self.getViewBrowser(repository)
        directions = find_tag_by_id(browser.contents, "push-directions")
        login_person(self.user)
        self.assertThat(extract_text(directions), DocTestMatches(dedent("""
            Update this repository:
            git push
            git+ssh://{username}@git.launchpad.dev/{repository.shortened_path}
            """).format(username=username, repository=repository),
            flags=doctest.NORMALIZE_WHITESPACE))

    def test_push_directions_logged_in_can_push_no_sshkeys(self):
        # If the user is logged in and can push to the repository but has no
        # SSH key registered, we point to the SSH keys form.
        repository = self.factory.makeGitRepository(owner=self.user)
        browser = self.getViewBrowser(repository)
        directions = find_tag_by_id(browser.contents, "ssh-key-directions")
        login_person(self.user)
        self.assertThat(directions.renderContents(), DocTestMatches(dedent("""
            To authenticate with the Launchpad Git hosting service, you need
            to <a href="http://launchpad.dev/~{user.name}/+editsshkeys">
            register an SSH key</a>.
            """).format(user=self.user),
            flags=doctest.NORMALIZE_WHITESPACE))

    def test_push_directions_logged_in_cannot_push_individual(self):
        # If the user is logged in but cannot push to a repository owned by
        # a person, we explain who can push.
        repository = self.factory.makeGitRepository()
        browser = self.getViewBrowser(repository)
        directions = find_tag_by_id(browser.contents, "push-directions")
        login_person(self.user)
        self.assertThat(directions.renderContents(), DocTestMatches(dedent("""
            You cannot push to this repository. Only <a
            href="http://launchpad.dev/~{owner.name}">{owner.display_name}</a>
            can push to this repository.
            """).format(owner=repository.owner),
            flags=doctest.NORMALIZE_WHITESPACE))

    def test_push_directions_logged_in_cannot_push_team(self):
        # If the user is logged in but cannot push to a repository owned by
        # a team, we explain who can push.
        team = self.factory.makeTeam()
        repository = self.factory.makeGitRepository(owner=team)
        browser = self.getViewBrowser(repository)
        directions = find_tag_by_id(browser.contents, "push-directions")
        login_person(self.user)
        self.assertThat(directions.renderContents(), DocTestMatches(dedent("""
            You cannot push to this repository. Members of <a
            href="http://launchpad.dev/~{owner.name}">{owner.display_name}</a>
            can push to this repository.
            """).format(owner=repository.owner),
            flags=doctest.NORMALIZE_WHITESPACE))

    def test_no_push_directions_for_imported_repository(self):
        # Imported repositories never show push directions.
        repository = self.factory.makeGitRepository(
            repository_type=GitRepositoryType.IMPORTED)
        browser = self.getViewBrowser(repository)
        self.assertIsNone(find_tag_by_id(browser.contents, "push-directions"))

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

    def test_view_with_active_reviews(self):
        repository = self.factory.makeGitRepository()
        git_refs = self.factory.makeGitRefs(
            repository,
            paths=["refs/heads/master", "refs/heads/1.0", "refs/tags/1.1"])
        self.factory.makeBranchMergeProposalForGit(
            target_ref=git_refs[0],
            set_state=BranchMergeProposalStatus.NEEDS_REVIEW)
        with FeatureFixture({"code.git.show_repository_mps": "on"}):
            with person_logged_in(repository.owner):
                browser = self.getViewBrowser(repository)
                self.assertIsNotNone(
                    find_tag_by_id(browser.contents, 'landing-candidates'))

    def test_landing_candidates_count(self):
        source_repository = self.factory.makeGitRepository()
        view = create_initialized_view(source_repository, '+index')

        self.assertEqual('No branches', view._getBranchCountText(0))
        self.assertEqual('1 branch', view._getBranchCountText(1))
        self.assertEqual('2 branches', view._getBranchCountText(2))

    def test_landing_candidates_query_count(self):
        repository = self.factory.makeGitRepository()
        git_refs = self.factory.makeGitRefs(
            repository,
            paths=["refs/heads/master", "refs/heads/1.0", "refs/tags/1.1"])

        def login_and_view():
            with FeatureFixture({"code.git.show_repository_mps": "on"}):
                with person_logged_in(repository.owner):
                    browser = self.getViewBrowser(repository)
                    self.assertIsNotNone(
                        find_tag_by_id(browser.contents, 'landing-candidates'))

        def create_merge_proposal():
            bmp = self.factory.makeBranchMergeProposalForGit(
                target_ref=git_refs[0],
                set_state=BranchMergeProposalStatus.NEEDS_REVIEW)
            self.factory.makePreviewDiff(merge_proposal=bmp)
            self.factory.makeCodeReviewComment(
                vote=CodeReviewVote.APPROVE, merge_proposal=bmp)

        recorder1, recorder2 = record_two_runs(
            login_and_view,
            create_merge_proposal,
            2)
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))

    def test_view_with_landing_targets(self):
        product = self.factory.makeProduct(name="foo", vcs=VCSType.GIT)
        target_repository = self.factory.makeGitRepository(target=product)
        source_repository = self.factory.makeGitRepository(target=product)
        [target_git_ref] = self.factory.makeGitRefs(
            target_repository,
            paths=["refs/heads/master"])
        [source_git_ref] = self.factory.makeGitRefs(
            source_repository,
            paths=["refs/heads/master"])
        self.factory.makeBranchMergeProposalForGit(
            target_ref=target_git_ref,
            source_ref=source_git_ref,
            set_state=BranchMergeProposalStatus.NEEDS_REVIEW)
        with FeatureFixture({"code.git.show_repository_mps": "on"}):
            with person_logged_in(target_repository.owner):
                browser = self.getViewBrowser(
                    source_repository, user=source_repository.owner)
                self.assertIsNotNone(
                    find_tag_by_id(browser.contents, 'landing-targets'))

    def test_landing_targets_query_count(self):
        product = self.factory.makeProduct(name="foo", vcs=VCSType.GIT)
        target_repository = self.factory.makeGitRepository(target=product)
        source_repository = self.factory.makeGitRepository(target=product)

        def create_merge_proposal():
            [target_git_ref] = self.factory.makeGitRefs(
                target_repository)
            [source_git_ref] = self.factory.makeGitRefs(
                source_repository)
            bmp = self.factory.makeBranchMergeProposalForGit(
                target_ref=target_git_ref,
                source_ref=source_git_ref,
                set_state=BranchMergeProposalStatus.NEEDS_REVIEW)
            self.factory.makePreviewDiff(merge_proposal=bmp)
            self.factory.makeCodeReviewComment(
                vote=CodeReviewVote.APPROVE, merge_proposal=bmp)

        def login_and_view():
            with FeatureFixture({"code.git.show_repository_mps": "on"}):
                with person_logged_in(target_repository.owner):
                    browser = self.getViewBrowser(
                        source_repository, user=source_repository.owner)
                    self.assertIsNotNone(
                        find_tag_by_id(browser.contents, 'landing-targets'))

        recorder1, recorder2 = record_two_runs(
            login_and_view,
            create_merge_proposal,
            2)
        # XXX cjwatson 2018-09-10: There is currently one extra
        # TeamParticipation query per reviewer (at least in this test setup)
        # due to GitRepository.isPersonTrustedReviewer.  Fixing this
        # probably requires a suitable helper to update Person._inTeam_cache
        # in bulk.
        self.assertThat(recorder2, HasQueryCount(Equals(recorder1.count + 2)))

    def test_view_with_inactive_landing_targets(self):
        product = self.factory.makeProduct(name="foo", vcs=VCSType.GIT)
        target_repository = self.factory.makeGitRepository(target=product)
        source_repository = self.factory.makeGitRepository(target=product)
        [target_git_ref] = self.factory.makeGitRefs(
            target_repository,
            paths=["refs/heads/master"])
        [source_git_ref] = self.factory.makeGitRefs(
            source_repository,
            paths=["refs/heads/master"])
        self.factory.makeBranchMergeProposalForGit(
            target_ref=target_git_ref,
            source_ref=source_git_ref,
            set_state=BranchMergeProposalStatus.MERGED)
        with FeatureFixture({"code.git.show_repository_mps": "on"}):
            with person_logged_in(target_repository.owner):
                browser = self.getViewBrowser(
                    source_repository, user=source_repository.owner)
                self.assertIsNone(
                    find_tag_by_id(browser.contents, 'landing-targets'))

    def test_query_count_subscriber_content(self):
        repository = self.factory.makeGitRepository()
        for _ in range(10):
            self.factory.makeGitSubscription(repository=repository)
        Store.of(repository).flush()
        Store.of(repository).invalidate()
        view = create_initialized_view(
            repository, "+repository-portlet-subscriber-content")
        with StormStatementRecorder() as recorder:
            view.render()
        self.assertThat(recorder, HasQueryCount(Equals(6)))


class TestGitRepositoryViewPrivateArtifacts(BrowserTestCase):
    """Tests that Git repositories with private team artifacts can be viewed.

    A repository may be associated with a private team as follows:
    - the owner is a private team
    - a subscriber is a private team

    A logged in user who is not authorised to see the private team(s) still
    needs to be able to view the repository.  The private team will be
    rendered in the normal way, displaying the team name and Launchpad URL.
    """

    layer = DatabaseFunctionalLayer

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

    def test_view_repository_with_private_subscriber(self):
        # A repository with a private subscriber is rendered.
        private_subscriber = self.factory.makeTeam(
            name="privateteam", visibility=PersonVisibility.PRIVATE)
        repository = self.factory.makeGitRepository()
        with person_logged_in(repository.owner):
            self.factory.makeGitSubscription(
                repository=repository, person=private_subscriber,
                subscribed_by=repository.owner)
        # Ensure the repository subscriber is rendered.
        url = canonical_url(repository, rootsite='code')
        user = self.factory.makePerson()
        browser = self._getBrowser(user)
        browser.open(url)
        soup = BeautifulSoup(browser.contents)
        self.assertIsNotNone(
            soup.find('div', attrs={'id': 'subscriber-privateteam'}))

    def test_anonymous_view_repository_with_private_subscriber(self):
        # Private repository subscribers are not rendered for anon users.
        private_subscriber = self.factory.makeTeam(
            name="privateteam", visibility=PersonVisibility.PRIVATE)
        repository = self.factory.makeGitRepository()
        with person_logged_in(private_subscriber):
            self.factory.makeGitSubscription(
                repository=repository, person=private_subscriber,
                subscribed_by=repository.owner)
        # Viewing the repository doesn't show the private subscriber.
        url = canonical_url(repository, rootsite='code')
        browser = self._getBrowser()
        browser.open(url)
        soup = BeautifulSoup(browser.contents)
        self.assertIsNone(
            soup.find('div', attrs={'id': 'subscriber-privateteam'}))

    def test_unsubscribe_private_repository(self):
        # Unsubscribing from a repository with a policy grant still allows
        # the repository to be seen.
        project = self.factory.makeProduct()
        owner = self.factory.makePerson()
        subscriber = self.factory.makePerson()
        [ap] = getUtility(IAccessPolicySource).find(
            [(project, InformationType.USERDATA)])
        self.factory.makeAccessPolicyGrant(
            policy=ap, grantee=subscriber, grantor=project.owner)
        repository = self.factory.makeGitRepository(
            target=project, owner=owner, name="repo",
            information_type=InformationType.USERDATA)
        with person_logged_in(owner):
            self.factory.makeGitSubscription(
                repository=repository, person=subscriber, subscribed_by=owner)
            base_url = canonical_url(repository, rootsite='code')
            expected_title = '%s : Git : Code : %s' % (
                repository.identity, project.displayname)
        url = '%s/+subscription/%s' % (base_url, subscriber.name)
        browser = self._getBrowser(user=subscriber)
        browser.open(url)
        browser.getControl('Unsubscribe').click()
        self.assertEqual(base_url, browser.url)
        self.assertEqual(expected_title, browser.title)

    def test_unsubscribe_private_repository_no_access(self):
        # Unsubscribing from a repository with no access will redirect to
        # the context of the repository.
        project = self.factory.makeProduct()
        owner = self.factory.makePerson()
        subscriber = self.factory.makePerson()
        repository = self.factory.makeGitRepository(
            target=project, owner=owner,
            information_type=InformationType.USERDATA)
        with person_logged_in(owner):
            self.factory.makeGitSubscription(
                repository=repository, person=subscriber, subscribed_by=owner)
            base_url = canonical_url(repository, rootsite='code')
            project_url = canonical_url(project, rootsite='code')
        url = '%s/+subscription/%s' % (base_url, subscriber.name)
        expected_title = "Code : %s" % project.displayname
        browser = self._getBrowser(user=subscriber)
        browser.open(url)
        browser.getControl('Unsubscribe').click()
        self.assertEqual(project_url, browser.url)
        self.assertEqual(expected_title, browser.title)


class TestGitRepositoryBranches(BrowserTestCase):
    """Test the listing of branches in a Git repository."""

    layer = DatabaseFunctionalLayer

    def makeRevisionAuthor(self, person=None):
        if person is None:
            person = self.factory.makePerson()
        email = removeSecurityProxy(person).preferredemail.email
        return getUtility(IRevisionSet).acquireRevisionAuthors([email])[email]

    def test_query_count(self):
        # The number of queries is constant in the number of refs.
        person = self.factory.makePerson()
        repository = self.factory.makeGitRepository(owner=person)
        now = datetime.now(pytz.UTC)

        def create_ref():
            with person_logged_in(person):
                [ref] = self.factory.makeGitRefs(repository=repository)
                naked_ref = removeSecurityProxy(ref)
                naked_ref.author = self.makeRevisionAuthor()
                naked_ref.author_date = now
                naked_ref.committer = self.makeRevisionAuthor()
                naked_ref.committer_date = now
                naked_ref.commit_message = "something"

        recorder1, recorder2 = record_two_runs(
            lambda: self.getMainText(repository, "+index"), create_ref, 10)
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))


class TestGitRepositoryEditReviewerView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_initial_reviewer_not_set(self):
        # If the reviewer is not set, the field is populated with the owner
        # of the repository.
        repository = self.factory.makeGitRepository()
        self.assertIsNone(repository.reviewer)
        view = create_view(repository, "+reviewer")
        self.assertEqual(repository.owner, view.initial_values["reviewer"])

    def test_initial_reviewer_set(self):
        # If the reviewer has been set, it is shown as the initial value.
        repository = self.factory.makeGitRepository()
        login_person(repository.owner)
        repository.reviewer = self.factory.makePerson()
        view = create_view(repository, "+reviewer")
        self.assertEqual(repository.reviewer, view.initial_values["reviewer"])

    def test_set_reviewer(self):
        # Test setting the reviewer.
        repository = self.factory.makeGitRepository()
        reviewer = self.factory.makePerson()
        login_person(repository.owner)
        view = create_initialized_view(repository, "+reviewer")
        view.change_action.success({"reviewer": reviewer})
        self.assertEqual(reviewer, repository.reviewer)
        # Last modified has been updated.
        self.assertSqlAttributeEqualsDate(
            repository, "date_last_modified", UTC_NOW)

    def test_set_reviewer_as_owner_clears_reviewer(self):
        # If the reviewer is set to be the repository owner, the review
        # field is cleared in the database.
        repository = self.factory.makeGitRepository()
        login_person(repository.owner)
        repository.reviewer = self.factory.makePerson()
        view = create_initialized_view(repository, "+reviewer")
        view.change_action.success({"reviewer": repository.owner})
        self.assertIsNone(repository.reviewer)
        # Last modified has been updated.
        self.assertSqlAttributeEqualsDate(
            repository, "date_last_modified", UTC_NOW)

    def test_set_reviewer_to_same_does_not_update_last_modified(self):
        # If the user has set the reviewer to be same and clicked on save,
        # then the underlying object hasn't really been changed, so the last
        # modified is not updated.
        modified_date = datetime(2007, 1, 1, tzinfo=pytz.UTC)
        repository = self.factory.makeGitRepository(date_created=modified_date)
        view = create_initialized_view(repository, "+reviewer")
        view.change_action.success({"reviewer": repository.owner})
        self.assertIsNone(repository.reviewer)
        # Last modified has not been updated.
        self.assertEqual(modified_date, repository.date_last_modified)


class TestGitRepositoryEditView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_repository_target_widget_read_only(self):
        # The repository target widget is read-only if the repository is the
        # default for its target.
        person = self.factory.makePerson()
        project = self.factory.makeProduct(owner=person)
        repository = self.factory.makeGitRepository(
            owner=person, target=project)
        login_person(person)
        repository.setTargetDefault(True)
        view = create_initialized_view(repository, name="+edit")
        self.assertEqual("project", view.widgets["target"].default_option)
        self.assertIsInstance(
            view.widgets["target"].project_widget, ItemDisplayWidget)
        self.assertEqual(
            project.title, view.widgets["target"].project_widget())

    def test_repository_target_widget_renders_personal(self):
        # The repository target widget renders correctly for a personal
        # repository.
        person = self.factory.makePerson()
        repository = self.factory.makeGitRepository(
            owner=person, target=person)
        login_person(person)
        view = create_initialized_view(repository, name="+edit")
        self.assertEqual("personal", view.widgets["target"].default_option)

    def test_repository_target_widget_renders_product(self):
        # The repository target widget renders correctly for a product
        # repository.
        person = self.factory.makePerson()
        project = self.factory.makeProduct()
        repository = self.factory.makeGitRepository(
            owner=person, target=project)
        login_person(person)
        view = create_initialized_view(repository, name="+edit")
        self.assertEqual("project", view.widgets["target"].default_option)
        self.assertEqual(
            project.name, view.widgets["target"].project_widget.selected_value)

    def test_repository_target_widget_renders_package(self):
        # The repository target widget renders correctly for a package
        # repository.
        person = self.factory.makePerson()
        dsp = self.factory.makeDistributionSourcePackage()
        repository = self.factory.makeGitRepository(owner=person, target=dsp)
        login_person(person)
        view = create_initialized_view(repository, name="+edit")
        self.assertEqual("package", view.widgets["target"].default_option)
        self.assertEqual(
            dsp.distribution,
            view.widgets["target"].distribution_widget._getFormValue())
        self.assertEqual(
            dsp.sourcepackagename.name,
            view.widgets["target"].package_widget.selected_value)

    def test_repository_target_widget_saves_personal(self):
        # The repository target widget can retarget to a personal
        # repository.
        person = self.factory.makePerson()
        repository = self.factory.makeGitRepository(owner=person)
        login_person(person)
        form = {
            "field.target": "personal",
            "field.actions.change": "Change Git Repository",
            }
        view = create_initialized_view(repository, name="+edit", form=form)
        self.assertEqual(person, repository.target)
        self.assertEqual(1, len(view.request.response.notifications))
        self.assertEqual(
            "This repository is now a personal repository for %s (%s)"
                % (person.displayname, person.name),
            view.request.response.notifications[0].message)

    def test_repository_target_widget_saves_personal_different_owner(self):
        # The repository target widget can retarget to a personal repository
        # for a different owner.
        person = self.factory.makePerson()
        repository = self.factory.makeGitRepository(
            owner=person, target=person)
        new_owner = self.factory.makeTeam(name="newowner", members=[person])
        login_person(person)
        form = {
            "field.target": "personal",
            "field.owner": "newowner",
            "field.actions.change": "Change Git Repository",
            }
        view = create_initialized_view(repository, name="+edit", form=form)
        self.assertEqual(new_owner, repository.target)
        self.assertEqual(1, len(view.request.response.notifications))
        self.assertEqual(
            "The repository owner has been changed to Newowner (newowner)",
            view.request.response.notifications[0].message)

    def test_repository_target_widget_saves_personal_clears_default(self):
        # When retargeting to a personal repository, the owner-target
        # default flag is cleared.
        person = self.factory.makePerson()
        project = self.factory.makeProduct(owner=person)
        repository = self.factory.makeGitRepository(
            owner=person, target=project)
        login_person(person)
        repository.setOwnerDefault(True)
        form = {
            "field.target": "personal",
            "field.actions.change": "Change Git Repository",
            }
        view = create_initialized_view(repository, name="+edit", form=form)
        self.assertEqual([], view.errors)
        self.assertEqual(person, repository.target)
        self.assertFalse(repository.owner_default)
        self.assertEqual(1, len(view.request.response.notifications))
        self.assertEqual(
            "This repository is now a personal repository for %s (%s)"
                % (person.displayname, person.name),
            view.request.response.notifications[0].message)

    def test_repository_target_widget_saves_project(self):
        # The repository target widget can retarget to a project repository.
        person = self.factory.makePerson()
        repository = self.factory.makeGitRepository(
            owner=person, target=person)
        project = self.factory.makeProduct()
        login_person(person)
        form = {
            "field.target": "project",
            "field.target.project": project.name,
            "field.actions.change": "Change Git Repository",
            }
        view = create_initialized_view(repository, name="+edit", form=form)
        self.assertEqual(project, repository.target)
        self.assertEqual(
            "The repository target has been changed to %s (%s)"
                % (project.displayname, project.name),
            view.request.response.notifications[0].message)

    def test_repository_target_widget_saves_package(self):
        # The repository target widget can retarget to a package repository.
        person = self.factory.makePerson()
        repository = self.factory.makeGitRepository(
            owner=person, target=person)
        dsp = self.factory.makeDistributionSourcePackage()
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=dsp.distribution.currentseries,
            sourcepackagename=dsp.sourcepackagename,
            archive=dsp.distribution.main_archive)
        login_person(person)
        form = {
            "field.target": "package",
            "field.target.distribution": dsp.distribution.name,
            "field.target.package": dsp.sourcepackagename.name,
            "field.actions.change": "Change Git Repository",
            }
        view = create_initialized_view(repository, name="+edit", form=form)
        self.assertEqual(dsp, repository.target)
        self.assertEqual(
            "The repository target has been changed to %s (%s)"
                % (dsp.displayname, dsp.name),
            view.request.response.notifications[0].message)

    def test_forbidden_target_is_error(self):
        # An error is displayed if a repository is saved with a target that
        # is not allowed by the sharing policy.
        owner = self.factory.makePerson()
        initial_target = self.factory.makeProduct()
        self.factory.makeProduct(
            name="commercial", owner=owner,
            branch_sharing_policy=BranchSharingPolicy.PROPRIETARY)
        repository = self.factory.makeGitRepository(
            owner=owner, target=initial_target,
            information_type=InformationType.PUBLIC)
        browser = self.getUserBrowser(
            canonical_url(repository) + "/+edit", user=owner)
        browser.getControl(name="field.target.project").value = "commercial"
        browser.getControl("Change Git Repository").click()
        self.assertThat(
            browser.contents,
            Contains(
                "Public repositories are not allowed for target Commercial."))
        with person_logged_in(owner):
            self.assertEqual(initial_target, repository.target)

    def test_default_conflict_is_error(self):
        # An error is displayed if an owner-default repository is saved with
        # a new target that already has an owner-default repository.
        owner = self.factory.makePerson()
        initial_target = self.factory.makeProduct()
        new_target = self.factory.makeProduct(name="new", displayname="New")
        repository = self.factory.makeGitRepository(
            owner=owner, target=initial_target)
        existing_default = self.factory.makeGitRepository(
            owner=owner, target=new_target)
        login_person(owner)
        repository.setOwnerDefault(True)
        existing_default.setOwnerDefault(True)
        browser = self.getUserBrowser(
            canonical_url(repository) + "/+edit", user=owner)
        browser.getControl(name="field.target.project").value = "new"
        browser.getControl("Change Git Repository").click()
        with person_logged_in(owner):
            self.assertThat(
                browser.contents,
                Contains(
                    "%s&#x27;s default repository for &#x27;New&#x27; is "
                    "already set to %s." %
                    (owner.displayname, existing_default.unique_name)))
            self.assertEqual(initial_target, repository.target)

    def test_rename(self):
        # The name of a repository can be changed via the UI by an
        # authorised user.
        person = self.factory.makePerson()
        repository = self.factory.makeGitRepository(owner=person, name="foo")
        browser = self.getUserBrowser(
            canonical_url(repository) + "/+edit", user=person)
        browser.getControl(name="field.name").value = "bar"
        browser.getControl("Change Git Repository").click()
        with person_logged_in(person):
            self.assertEqual("bar", repository.name)

    def test_change_owner(self):
        # An authorised user can change the owner to a team they're a member
        # of.
        person = self.factory.makePerson()
        team = self.factory.makeTeam(name="newowner", members=[person])
        repository = self.factory.makeGitRepository(owner=person)
        browser = self.getUserBrowser(
            canonical_url(repository) + "/+edit", user=person)
        browser.getControl(name="field.owner").value = ["newowner"]
        browser.getControl("Change Git Repository").click()
        with person_logged_in(person):
            self.assertEqual(team, repository.owner)

    def test_change_owner_personal(self):
        # An authorised user can change the owner of a personal repository
        # to a team they're a member of.
        person = self.factory.makePerson()
        team = self.factory.makeTeam(name="newowner", members=[person])
        repository = self.factory.makeGitRepository(
            owner=person, target=person)
        browser = self.getUserBrowser(
            canonical_url(repository) + "/+edit", user=person)
        browser.getControl(name="field.owner").value = ["newowner"]
        browser.getControl("Change Git Repository").click()
        with person_logged_in(person):
            self.assertEqual(team, repository.owner)
            self.assertEqual(team, repository.target)

    def test_cannot_change_owner_to_foreign_team(self):
        # A user cannot change the owner of their repository to a team
        # they're not a member of.
        person = self.factory.makePerson()
        self.factory.makeTeam(name="newowner")
        repository = self.factory.makeGitRepository(owner=person)
        browser = self.getUserBrowser(
            canonical_url(repository) + "/+edit", user=person)
        self.assertNotIn(
            "newowner", browser.getControl(name="field.owner").options)

    def test_information_type_in_ui(self):
        # The information_type of a repository can be changed via the UI by
        # an authorised user.
        person = self.factory.makePerson()
        repository = self.factory.makeGitRepository(owner=person)
        admin = getUtility(ILaunchpadCelebrities).admin.teamowner
        browser = self.getUserBrowser(
            canonical_url(repository) + "/+edit", user=admin)
        browser.getControl("Private", index=1).click()
        browser.getControl("Change Git Repository").click()
        with person_logged_in(person):
            self.assertEqual(
                InformationType.USERDATA, repository.information_type)

    def test_edit_view_ajax_render(self):
        # An information type change request is processed as expected when
        # an XHR request is made to the view.
        person = self.factory.makePerson()
        repository = self.factory.makeGitRepository(owner=person)

        extra = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}
        request = LaunchpadTestRequest(
            method="POST", form={
                "field.actions.change": "Change Git Repository",
                "field.information_type": "PUBLICSECURITY"},
            **extra)
        with person_logged_in(person):
            view = create_initialized_view(
                repository, name="+edit-information-type",
                request=request, principal=person)
            request.traversed_objects = [
                person, repository.target, repository, view]
            result = view.render()
            self.assertEqual("", result)
            self.assertEqual(
                repository.information_type, InformationType.PUBLICSECURITY)

    def test_change_default_branch(self):
        # An authorised user can change the default branch to one that
        # exists.  They may omit "refs/heads/".
        hosting_fixture = self.useFixture(GitHostingFixture())
        person = self.factory.makePerson()
        repository = self.factory.makeGitRepository(owner=person)
        master, new = self.factory.makeGitRefs(
            repository=repository,
            paths=["refs/heads/master", "refs/heads/new"])
        removeSecurityProxy(repository)._default_branch = "refs/heads/master"
        browser = self.getUserBrowser(
            canonical_url(repository) + "/+edit", user=person)
        browser.getControl(name="field.default_branch").value = "new"
        browser.getControl("Change Git Repository").click()
        with person_logged_in(person):
            self.assertEqual(
                [((repository.getInternalPath(),),
                 {"default_branch": "refs/heads/new"})],
                hosting_fixture.setProperties.calls)
            self.assertEqual("refs/heads/new", repository.default_branch)

    def test_change_default_branch_nonexistent(self):
        # Trying to change the default branch to one that doesn't exist
        # displays an error.
        person = self.factory.makePerson()
        repository = self.factory.makeGitRepository(owner=person)
        [master] = self.factory.makeGitRefs(
            repository=repository, paths=["refs/heads/master"])
        removeSecurityProxy(repository)._default_branch = "refs/heads/master"
        form = {
            "field.default_branch": "refs/heads/new",
            "field.actions.change": "Change Git Repository",
            }
        transaction.commit()
        with person_logged_in(person):
            view = create_initialized_view(repository, name="+edit", form=form)
        self.assertEqual(
            ["This repository does not contain a reference named "
             "&#x27;refs/heads/new&#x27;."],
            view.errors)
        self.assertEqual("refs/heads/master", repository.default_branch)


class TestGitRepositoryEditViewInformationTypes(TestCaseWithFactory):
    """Tests for GitRepositoryEditView.getInformationTypesToShow."""

    layer = DatabaseFunctionalLayer

    def assertShownTypes(self, types, repository, user=None):
        if user is None:
            user = removeSecurityProxy(repository).owner
        with person_logged_in(user):
            view = create_initialized_view(repository, "+edit", principal=user)
            self.assertContentEqual(types, view.getInformationTypesToShow())

    def test_public_repository(self):
        # A normal public repository on a public project can be any
        # information type except embargoed and proprietary.
        # The model doesn't enforce this, so it's just a UI thing.
        repository = self.factory.makeGitRepository(
            information_type=InformationType.PUBLIC)
        self.assertShownTypes(
            [InformationType.PUBLIC, InformationType.PUBLICSECURITY,
             InformationType.PRIVATESECURITY, InformationType.USERDATA],
            repository)

    def test_repository_with_disallowed_type(self):
        # We don't force repositories with a disallowed type (e.g.
        # Proprietary on a non-commercial project) to change, so the current
        # type is shown.
        project = self.factory.makeProduct()
        self.factory.makeAccessPolicy(pillar=project)
        repository = self.factory.makeGitRepository(
            target=project, information_type=InformationType.PROPRIETARY)
        self.assertShownTypes(
            [InformationType.PUBLIC, InformationType.PUBLICSECURITY,
             InformationType.PRIVATESECURITY, InformationType.USERDATA,
             InformationType.PROPRIETARY], repository)

    def test_repository_for_project_with_embargoed_and_proprietary(self):
        # Repositories for commercial projects which have a policy of
        # embargoed or proprietary allow only embargoed and proprietary
        # types.
        owner = self.factory.makePerson()
        project = self.factory.makeProduct(owner=owner)
        self.factory.makeCommercialSubscription(product=project)
        with person_logged_in(owner):
            project.setBranchSharingPolicy(
                BranchSharingPolicy.EMBARGOED_OR_PROPRIETARY)
            repository = self.factory.makeGitRepository(
                owner=owner, target=project,
                information_type=InformationType.PROPRIETARY)
        self.assertShownTypes(
            [InformationType.EMBARGOED, InformationType.PROPRIETARY],
            repository)

    def test_repository_for_project_with_proprietary(self):
        # Repositories for commercial projects which have a policy of
        # proprietary allow only the proprietary type.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct(owner=owner)
        self.factory.makeCommercialSubscription(product=product)
        with person_logged_in(owner):
            product.setBranchSharingPolicy(BranchSharingPolicy.PROPRIETARY)
            repository = self.factory.makeGitRepository(
                owner=owner, target=product,
                information_type=InformationType.PROPRIETARY)
        self.assertShownTypes([InformationType.PROPRIETARY], repository)


class TestGitRepositoryDiffView(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def test_render(self):
        diff = "A fake diff\n"
        hosting_fixture = self.useFixture(GitHostingFixture(
            diff={"patch": diff}))
        person = self.factory.makePerson()
        repository = self.factory.makeGitRepository(
            owner=person, name="some-repository")
        browser = self.getUserBrowser(
            canonical_url(repository) + "/+diff/0123456/0123456^")
        with person_logged_in(person):
            self.assertEqual(
                [((repository.getInternalPath(), "0123456^", "0123456"), {})],
                hosting_fixture.getDiff.calls)
        self.assertEqual(
            'text/x-patch;charset=UTF-8', browser.headers["Content-Type"])
        self.assertEqual(str(len(diff)), browser.headers["Content-Length"])
        self.assertEqual(
            'attachment; filename="some-repository_0123456^_0123456.diff"',
            browser.headers["Content-Disposition"])
        self.assertEqual(diff, browser.contents)

    def test_security(self):
        # A user who can see a private repository can fetch diffs from it,
        # but other users cannot.
        diff = "A fake diff\n"
        self.useFixture(GitHostingFixture(diff={"patch": diff}))
        person = self.factory.makePerson()
        project = self.factory.makeProduct(
            owner=person, information_type=InformationType.PROPRIETARY)
        with person_logged_in(person):
            repository = self.factory.makeGitRepository(
                owner=person, target=project,
                information_type=InformationType.PROPRIETARY)
            repository_url = canonical_url(repository)
        browser = self.getUserBrowser(
            repository_url + "/+diff/0123456/0123456^", user=person)
        self.assertEqual(diff, browser.contents)
        self.useFixture(FakeLogger())
        self.assertRaises(
            Unauthorized, self.getUserBrowser,
            repository_url + "/+diff/0123456/0123456^")

    def test_filename_quoting(self):
        # If we construct revisions containing metacharacters and somehow
        # manage to get that past the hosting service, the
        # Content-Disposition header is quoted properly.
        diff = "A fake diff\n"
        self.useFixture(GitHostingFixture(diff={"patch": diff}))
        person = self.factory.makePerson()
        repository = self.factory.makeGitRepository(
            owner=person, name="some-repository")
        browser = self.getUserBrowser(
            canonical_url(repository) + '/+diff/foo"/"bar')
        self.assertEqual(
            r'attachment; filename="some-repository_\"bar_foo\".diff"',
            browser.headers["Content-Disposition"])


class TestGitRepositoryPermissionsView(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def test_rules_properties(self):
        repository = self.factory.makeGitRepository()
        heads_rule = self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/*")
        tags_rule = self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/tags/*")
        catch_all_rule = self.factory.makeGitRule(
            repository=repository, ref_pattern="*")
        login_person(repository.owner)
        view = create_initialized_view(repository, name="+permissions")
        self.assertEqual([heads_rule], view.branch_rules)
        self.assertEqual([tags_rule], view.tag_rules)
        self.assertEqual([catch_all_rule], view.other_rules)

    def test__getRuleGrants(self):
        rule = self.factory.makeGitRule()
        grantees = sorted(
            [self.factory.makePerson() for _ in range(3)],
            key=attrgetter("name"))
        for grantee in (grantees[1], grantees[0], grantees[2]):
            self.factory.makeGitRuleGrant(rule=rule, grantee=grantee)
        self.factory.makeGitRuleGrant(
            rule=rule, grantee=GitGranteeType.REPOSITORY_OWNER)
        login_person(rule.repository.owner)
        view = create_initialized_view(rule.repository, name="+permissions")
        self.assertThat(view._getRuleGrants(rule), MatchesListwise([
            MatchesStructure.byEquality(
                grantee_type=GitGranteeType.REPOSITORY_OWNER),
            MatchesStructure.byEquality(grantee=grantees[0]),
            MatchesStructure.byEquality(grantee=grantees[1]),
            MatchesStructure.byEquality(grantee=grantees[2]),
            ]))

    def test__parseRefPattern(self):
        repository = self.factory.makeGitRepository()
        login_person(repository.owner)
        view = create_initialized_view(repository, name="+permissions")
        self.assertEqual(
            ("refs/heads/", "stable/*"),
            view._parseRefPattern("refs/heads/stable/*"))
        self.assertEqual(
            ("refs/tags/", "1.0"), view._parseRefPattern("refs/tags/1.0"))
        self.assertEqual(
            ("", "refs/other/*"), view._parseRefPattern("refs/other/*"))
        self.assertEqual(("", "*"), view._parseRefPattern("*"))

    def test__getFieldName_no_grantee(self):
        repository = self.factory.makeGitRepository()
        login_person(repository.owner)
        view = create_initialized_view(repository, name="+permissions")
        encoded_ref_pattern = base64.b32encode(
            b"refs/heads/*").replace("=", "_").decode("UTF-8")
        self.assertEqual(
            "field.%s" % encoded_ref_pattern,
            view._getFieldName("field", "refs/heads/*"))

    def test__getFieldName_grantee_repository_owner(self):
        repository = self.factory.makeGitRepository()
        login_person(repository.owner)
        view = create_initialized_view(repository, name="+permissions")
        encoded_ref_pattern = base64.b32encode(
            b"refs/tags/*").replace("=", "_").decode("UTF-8")
        self.assertEqual(
            "field.%s._repository_owner" % encoded_ref_pattern,
            view._getFieldName(
                "field", "refs/tags/*",
                grantee=GitGranteeType.REPOSITORY_OWNER))

    def test__getFieldName_grantee_person(self):
        repository = self.factory.makeGitRepository()
        grantee = self.factory.makePerson()
        login_person(repository.owner)
        view = create_initialized_view(repository, name="+permissions")
        encoded_ref_pattern = base64.b32encode(
            b"refs/*").replace("=", "_").decode("UTF-8")
        self.assertEqual(
            "field.%s.%s" % (encoded_ref_pattern, grantee.id),
            view._getFieldName("field", "refs/*", grantee=grantee))

    def test__parseFieldName_too_few_components(self):
        repository = self.factory.makeGitRepository()
        login_person(repository.owner)
        view = create_initialized_view(repository, name="+permissions")
        self.assertRaises(UnexpectedFormData, view._parseFieldName, "field")

    def test__parseFieldName_bad_ref_pattern(self):
        repository = self.factory.makeGitRepository()
        login_person(repository.owner)
        view = create_initialized_view(repository, name="+permissions")
        self.assertRaises(
            UnexpectedFormData, view._parseFieldName, "field.nonsense")

    def test__parseFieldName_no_grantee(self):
        repository = self.factory.makeGitRepository()
        login_person(repository.owner)
        view = create_initialized_view(repository, name="+permissions")
        encoded_ref_pattern = base64.b32encode(
            b"refs/heads/*").replace("=", "_").decode("UTF-8")
        self.assertEqual(
            ("permissions", "refs/heads/*", None),
            view._parseFieldName("permissions.%s" % encoded_ref_pattern))

    def test__parseFieldName_grantee_unknown_type(self):
        repository = self.factory.makeGitRepository()
        login_person(repository.owner)
        view = create_initialized_view(repository, name="+permissions")
        encoded_ref_pattern = base64.b32encode(
            b"refs/tags/*").replace("=", "_").decode("UTF-8")
        self.assertRaises(
            UnexpectedFormData, view._parseFieldName,
            "field.%s._nonsense" % encoded_ref_pattern)
        self.assertRaises(
            UnexpectedFormData, view._parseFieldName,
            "field.%s._person" % encoded_ref_pattern)

    def test__parseFieldName_grantee_repository_owner(self):
        repository = self.factory.makeGitRepository()
        login_person(repository.owner)
        view = create_initialized_view(repository, name="+permissions")
        encoded_ref_pattern = base64.b32encode(
            b"refs/tags/*").replace("=", "_").decode("UTF-8")
        self.assertEqual(
            ("pattern", "refs/tags/*", GitGranteeType.REPOSITORY_OWNER),
            view._parseFieldName(
                "pattern.%s._repository_owner" % encoded_ref_pattern))

    def test__parseFieldName_grantee_unknown_person(self):
        repository = self.factory.makeGitRepository()
        grantee = self.factory.makePerson()
        login_person(repository.owner)
        view = create_initialized_view(repository, name="+permissions")
        encoded_ref_pattern = base64.b32encode(
            b"refs/*").replace("=", "_").decode("UTF-8")
        self.assertRaises(
            UnexpectedFormData, view._parseFieldName,
            "delete.%s.%s" % (encoded_ref_pattern, grantee.id * 2))

    def test__parseFieldName_grantee_person(self):
        repository = self.factory.makeGitRepository()
        grantee = self.factory.makePerson()
        login_person(repository.owner)
        view = create_initialized_view(repository, name="+permissions")
        encoded_ref_pattern = base64.b32encode(
            b"refs/*").replace("=", "_").decode("UTF-8")
        self.assertEqual(
            ("delete", "refs/*", grantee),
            view._parseFieldName(
                "delete.%s.%s" % (encoded_ref_pattern, grantee.id)))

    def test__getPermissionsTerm_standard(self):
        grant = self.factory.makeGitRuleGrant(
            ref_pattern="refs/heads/*", can_create=True, can_push=True)
        login_person(grant.repository.owner)
        view = create_initialized_view(grant.repository, name="+permissions")
        self.assertThat(
            view._getPermissionsTerm(grant), MatchesStructure.byEquality(
                value={
                    GitPermissionType.CAN_CREATE, GitPermissionType.CAN_PUSH},
                token="can_push",
                title="Can push"))

    def test__getPermissionsTerm_custom(self):
        grant = self.factory.makeGitRuleGrant(
            ref_pattern="refs/heads/*", can_force_push=True)
        login_person(grant.repository.owner)
        view = create_initialized_view(grant.repository, name="+permissions")
        self.assertThat(
            view._getPermissionsTerm(grant), MatchesStructure.byEquality(
                value={GitPermissionType.CAN_FORCE_PUSH},
                token="custom",
                title="Custom permissions: force-push"))

    def _matchesCells(self, row_tag, cell_matchers):
        return AfterPreprocessing(
            str, soupmatchers.HTMLContains(*(
                soupmatchers.Within(row_tag, cell_matcher)
                for cell_matcher in cell_matchers)))

    def _matchesRule(self, position, pattern, short_pattern):
        rule_tag = soupmatchers.Tag(
            "rule row", "tr", attrs={"class": "git-rule"})
        suffix = "." + encode_form_field_id(pattern)
        position_field_name = "field.position" + suffix
        pattern_field_name = "field.pattern" + suffix
        delete_field_name = "field.delete" + suffix
        return self._matchesCells(rule_tag, [
            soupmatchers.Within(
                soupmatchers.Tag("position cell", "td"),
                soupmatchers.Tag(
                    "position widget", "input",
                    attrs={"name": position_field_name, "value": position})),
            soupmatchers.Within(
                soupmatchers.Tag("pattern cell", "td"),
                soupmatchers.Tag(
                    "pattern widget", "input",
                    attrs={
                        "name": pattern_field_name,
                        "value": short_pattern,
                        })),
            soupmatchers.Within(
                soupmatchers.Tag("delete cell", "td"),
                soupmatchers.Tag(
                    "delete widget", "input",
                    attrs={"name": delete_field_name})),
            ])

    def _matchesNewRule(self, ref_prefix):
        new_rule_tag = soupmatchers.Tag(
            "new rule row", "tr", attrs={"class": "git-new-rule"})
        suffix = "." + encode_form_field_id(ref_prefix)
        new_position_field_name = "field.new-position" + suffix
        new_pattern_field_name = "field.new-pattern" + suffix
        return self._matchesCells(new_rule_tag, [
            soupmatchers.Within(
                soupmatchers.Tag("position cell", "td"),
                soupmatchers.Tag(
                    "position widget", "input",
                    attrs={"name": new_position_field_name, "value": ""})),
            soupmatchers.Within(
                soupmatchers.Tag("pattern cell", "td"),
                soupmatchers.Tag(
                    "pattern widget", "input",
                    attrs={"name": new_pattern_field_name, "value": ""})),
            ])

    def _matchesRuleGrant(self, pattern, grantee, permissions_token,
                          permissions_title):
        rule_grant_tag = soupmatchers.Tag(
            "rule grant row", "tr", attrs={"class": "git-rule-grant"})
        suffix = "." + encode_form_field_id(pattern)
        if IPerson.providedBy(grantee):
            suffix += "." + str(grantee.id)
            grantee_widget_matcher = soupmatchers.Tag(
                "grantee widget", "a", attrs={"href": canonical_url(grantee)},
                text=" " + grantee.display_name)
        else:
            suffix += "._" + grantee.name.lower()
            grantee_widget_matcher = soupmatchers.Tag(
                "grantee widget", "label",
                text=re.compile(re.escape(grantee.title)))
        permissions_field_name = "field.permissions" + suffix
        delete_field_name = "field.delete" + suffix
        return self._matchesCells(rule_grant_tag, [
            soupmatchers.Within(
                soupmatchers.Tag("grantee cell", "td"),
                grantee_widget_matcher),
            soupmatchers.Within(
                soupmatchers.Tag("permissions cell", "td"),
                soupmatchers.Within(
                    soupmatchers.Tag(
                        "permissions widget", "select",
                        attrs={"name": permissions_field_name}),
                    soupmatchers.Tag(
                        "selected permissions option", "option",
                        attrs={
                            "selected": "selected",
                            "value": permissions_token,
                            },
                        text=permissions_title))),
            soupmatchers.Within(
                soupmatchers.Tag("delete cell", "td"),
                soupmatchers.Tag(
                    "delete widget", "input",
                    attrs={"name": delete_field_name})),
            ])

    def _matchesNewRuleGrant(self, pattern, permissions_token):
        rule_grant_tag = soupmatchers.Tag(
            "rule grant row", "tr", attrs={"class": "git-new-rule-grant"})
        suffix = "." + encode_form_field_id(pattern)
        grantee_field_name = "field.grantee" + suffix
        permissions_field_name = "field.permissions" + suffix
        return self._matchesCells(rule_grant_tag, [
            soupmatchers.Within(
                soupmatchers.Tag("grantee cell", "td"),
                soupmatchers.Tag(
                    "grantee widget", "input",
                    attrs={"name": grantee_field_name})),
            soupmatchers.Within(
                soupmatchers.Tag("permissions cell", "td"),
                soupmatchers.Within(
                    soupmatchers.Tag(
                        "permissions widget", "select",
                        attrs={"name": permissions_field_name}),
                    soupmatchers.Tag(
                        "selected permissions option", "option",
                        attrs={
                            "selected": "selected",
                            "value": permissions_token,
                            }))),
            ])

    def test_rules_table(self):
        repository = self.factory.makeGitRepository()
        heads_rule = self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/stable/*")
        heads_grantee_1 = self.factory.makePerson(
            name=self.factory.getUniqueString("person-name-a"))
        heads_grantee_2 = self.factory.makePerson(
            name=self.factory.getUniqueString("person-name-b"))
        self.factory.makeGitRuleGrant(
            rule=heads_rule, grantee=heads_grantee_1, can_push=True)
        self.factory.makeGitRuleGrant(
            rule=heads_rule, grantee=heads_grantee_2, can_force_push=True)
        tags_rule = self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/tags/*")
        self.factory.makeGitRuleGrant(
            rule=tags_rule, grantee=GitGranteeType.REPOSITORY_OWNER)
        login_person(repository.owner)
        view = create_initialized_view(
            repository, name="+permissions", principal=repository.owner)
        rules_table = find_tag_by_id(view(), "rules-table")
        rows = rules_table.findAll("tr", {"class": True})
        self.assertThat(rows, MatchesListwise([
            self._matchesRule("1", "refs/heads/stable/*", "stable/*"),
            self._matchesRuleGrant(
                "refs/heads/stable/*", heads_grantee_1, "can_push_existing",
                "Can push if the branch already exists"),
            self._matchesRuleGrant(
                "refs/heads/stable/*", heads_grantee_2, "custom",
                "Custom permissions: force-push"),
            self._matchesNewRuleGrant("refs/heads/stable/*", "can_push"),
            self._matchesNewRule("refs/heads/"),
            self._matchesRule("2", "refs/tags/*", "*"),
            self._matchesRuleGrant(
                "refs/tags/*", GitGranteeType.REPOSITORY_OWNER,
                "cannot_create", "Cannot create"),
            self._matchesNewRuleGrant("refs/tags/*", "can_create"),
            self._matchesNewRule("refs/tags/"),
            ]))

    def assertHasRules(self, repository, ref_patterns):
        self.assertThat(list(repository.rules), MatchesListwise([
            MatchesStructure.byEquality(ref_pattern=ref_pattern)
            for ref_pattern in ref_patterns
            ]))

    def assertHasSavedNotification(self, view, repository):
        self.assertThat(view.request.response.notifications, MatchesListwise([
            MatchesStructure.byEquality(
                message="Saved permissions for %s" % repository.identity),
            ]))

    def test_save_add_rules(self):
        repository = self.factory.makeGitRepository()
        self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/stable/*")
        removeSecurityProxy(repository.getActivity()).remove()
        login_person(repository.owner)
        encoded_heads_prefix = encode_form_field_id("refs/heads/")
        encoded_tags_prefix = encode_form_field_id("refs/tags/")
        form = {
            "field.new-pattern." + encoded_heads_prefix: "*",
            "field.new-pattern." + encoded_tags_prefix: "1.0",
            "field.actions.save": "Save",
            }
        view = create_initialized_view(
            repository, name="+permissions", form=form,
            principal=repository.owner)
        self.assertHasRules(
            repository,
            ["refs/tags/1.0", "refs/heads/stable/*", "refs/heads/*"])
        self.assertThat(list(repository.getActivity()), MatchesListwise([
            # Adding a tag rule automatically adds a repository owner grant.
            MatchesStructure(
                changer=Equals(repository.owner),
                changee=Is(None),
                what_changed=Equals(GitActivityType.GRANT_ADDED),
                new_value=MatchesDict({
                    "changee_type": Equals("Repository owner"),
                    "ref_pattern": Equals("refs/tags/1.0"),
                    "can_create": Is(True),
                    "can_push": Is(False),
                    "can_force_push": Is(False),
                    })),
            MatchesStructure(
                changer=Equals(repository.owner),
                what_changed=Equals(GitActivityType.RULE_ADDED),
                new_value=MatchesDict({
                    "ref_pattern": Equals("refs/tags/1.0"),
                    "position": Equals(0),
                    })),
            MatchesStructure(
                changer=Equals(repository.owner),
                what_changed=Equals(GitActivityType.RULE_ADDED),
                new_value=MatchesDict({
                    "ref_pattern": Equals("refs/heads/*"),
                    # Initially inserted at 1, although refs/tags/1.0 was
                    # later inserted before it.
                    "position": Equals(1),
                    })),
            ]))
        self.assertHasSavedNotification(view, repository)

    def test_save_add_duplicate_rule(self):
        repository = self.factory.makeGitRepository()
        self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/stable/*")
        transaction.commit()
        login_person(repository.owner)
        encoded_heads_prefix = encode_form_field_id("refs/heads/")
        form = {
            "field.new-pattern." + encoded_heads_prefix: "stable/*",
            "field.actions.save": "Save",
            }
        view = create_initialized_view(
            repository, name="+permissions", form=form,
            principal=repository.owner)
        self.assertThat(view.errors, MatchesListwise([
            MatchesStructure(
                field_name=Equals("new-pattern." + encoded_heads_prefix),
                errors=MatchesStructure.byEquality(
                    args=("stable/* is already in use by another rule",))),
            ]))
        self.assertHasRules(repository, ["refs/heads/stable/*"])

    def test_save_move_rule(self):
        repository = self.factory.makeGitRepository()
        self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/stable/*")
        self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/*/next")
        encoded_patterns = [
            encode_form_field_id(rule.ref_pattern)
            for rule in repository.rules]
        removeSecurityProxy(repository.getActivity()).remove()
        login_person(repository.owner)
        # Positions are 1-based in the UI.
        form = {
            "field.position." + encoded_patterns[0]: "2",
            "field.pattern." + encoded_patterns[0]: "stable/*",
            "field.position." + encoded_patterns[1]: "1",
            "field.pattern." + encoded_patterns[1]: "*/more-next",
            "field.actions.save": "Save",
            }
        view = create_initialized_view(
            repository, name="+permissions", form=form,
            principal=repository.owner)
        self.assertHasRules(
            repository, ["refs/heads/*/more-next", "refs/heads/stable/*"])
        self.assertThat(list(repository.getActivity()), MatchesListwise([
            MatchesStructure(
                changer=Equals(repository.owner),
                what_changed=Equals(GitActivityType.RULE_CHANGED),
                old_value=MatchesDict({
                    "ref_pattern": Equals("refs/heads/*/next"),
                    "position": Equals(0),
                    }),
                new_value=MatchesDict({
                    "ref_pattern": Equals("refs/heads/*/more-next"),
                    "position": Equals(0),
                    })),
            # Only one rule is recorded as moving; the other is already in
            # its new position by the time it's processed.
            MatchesStructure(
                changer=Equals(repository.owner),
                what_changed=Equals(GitActivityType.RULE_MOVED),
                old_value=MatchesDict({
                    "ref_pattern": Equals("refs/heads/stable/*"),
                    "position": Equals(0),
                    }),
                new_value=MatchesDict({
                    "ref_pattern": Equals("refs/heads/stable/*"),
                    "position": Equals(1),
                    })),
            ]))
        self.assertHasSavedNotification(view, repository)

    def test_save_change_grants(self):
        repository = self.factory.makeGitRepository()
        stable_rule = self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/stable/*")
        next_rule = self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/*/next")
        grantees = [self.factory.makePerson() for _ in range(3)]
        self.factory.makeGitRuleGrant(
            rule=stable_rule, grantee=GitGranteeType.REPOSITORY_OWNER,
            can_create=True)
        self.factory.makeGitRuleGrant(
            rule=stable_rule,
            grantee=grantees[0], can_create=True, can_push=True)
        self.factory.makeGitRuleGrant(
            rule=next_rule, grantee=grantees[1],
            can_create=True, can_push=True, can_force_push=True)
        encoded_patterns = [
            encode_form_field_id(rule.ref_pattern)
            for rule in repository.rules]
        removeSecurityProxy(repository.getActivity()).remove()
        login_person(repository.owner)
        form = {
            "field.permissions.%s._repository_owner" % encoded_patterns[0]: (
                "can_push"),
            "field.permissions.%s.%s" % (
                encoded_patterns[0], grantees[0].id): "can_push",
            "field.delete.%s.%s" % (encoded_patterns[0], grantees[0].id): "on",
            "field.grantee.%s" % encoded_patterns[1]: "person",
            "field.grantee.%s.person" % encoded_patterns[1]: grantees[2].name,
            "field.permissions.%s" % encoded_patterns[1]: "can_push_existing",
            "field.actions.save": "Save",
            }
        view = create_initialized_view(
            repository, name="+permissions", form=form,
            principal=repository.owner)
        self.assertHasRules(
            repository, ["refs/heads/stable/*", "refs/heads/*/next"])
        self.assertThat(stable_rule.grants, MatchesSetwise(
            MatchesStructure.byEquality(
                grantee_type=GitGranteeType.REPOSITORY_OWNER,
                can_create=True, can_push=True, can_force_push=False)))
        self.assertThat(next_rule.grants, MatchesSetwise(
            MatchesStructure.byEquality(
                grantee=grantees[1],
                can_create=True, can_push=True, can_force_push=True),
            MatchesStructure.byEquality(
                grantee=grantees[2],
                can_create=False, can_push=True, can_force_push=False)))
        self.assertThat(repository.getActivity(), MatchesSetwise(
            MatchesStructure(
                changer=Equals(repository.owner),
                changee=Is(None),
                what_changed=Equals(GitActivityType.GRANT_CHANGED),
                old_value=Equals({
                    "changee_type": "Repository owner",
                    "ref_pattern": "refs/heads/stable/*",
                    "can_create": True,
                    "can_push": False,
                    "can_force_push": False,
                    }),
                new_value=Equals({
                    "changee_type": "Repository owner",
                    "ref_pattern": "refs/heads/stable/*",
                    "can_create": True,
                    "can_push": True,
                    "can_force_push": False,
                    })),
            MatchesStructure(
                changer=Equals(repository.owner),
                changee=Equals(grantees[0]),
                what_changed=Equals(GitActivityType.GRANT_REMOVED),
                old_value=Equals({
                    "changee_type": "Person",
                    "ref_pattern": "refs/heads/stable/*",
                    "can_create": True,
                    "can_push": True,
                    "can_force_push": False,
                    })),
            MatchesStructure(
                changer=Equals(repository.owner),
                changee=Equals(grantees[2]),
                what_changed=Equals(GitActivityType.GRANT_ADDED),
                new_value=Equals({
                    "changee_type": "Person",
                    "ref_pattern": "refs/heads/*/next",
                    "can_create": False,
                    "can_push": True,
                    "can_force_push": False,
                    }))))
        self.assertHasSavedNotification(view, repository)

    def test_save_delete_rule(self):
        repository = self.factory.makeGitRepository()
        self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/stable/*")
        self.factory.makeGitRule(
            repository=repository, ref_pattern="refs/heads/*")
        removeSecurityProxy(repository.getActivity()).remove()
        login_person(repository.owner)
        encoded_pattern = encode_form_field_id("refs/heads/*")
        form = {
            "field.pattern." + encoded_pattern: "*",
            "field.delete." + encoded_pattern: "on",
            "field.actions.save": "Save",
            }
        view = create_initialized_view(
            repository, name="+permissions", form=form,
            principal=repository.owner)
        self.assertHasRules(repository, ["refs/heads/stable/*"])
        self.assertThat(list(repository.getActivity()), MatchesListwise([
            MatchesStructure(
                changer=Equals(repository.owner),
                what_changed=Equals(GitActivityType.RULE_REMOVED),
                old_value=MatchesDict({
                    "ref_pattern": Equals("refs/heads/*"),
                    "position": Equals(1),
                    })),
            ]))
        self.assertHasSavedNotification(view, repository)


class TestGitRepositoryDeletionView(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def test_repository_has_delete_link(self):
        # A newly-created repository has a "Delete repository" link.
        repository = self.factory.makeGitRepository()
        delete_url = canonical_url(
            repository, view_name="+delete", rootsite="code")
        browser = self.getViewBrowser(
            repository, "+index", rootsite="code", user=repository.owner)
        delete_link = browser.getLink("Delete repository")
        self.assertEqual(delete_url, delete_link.url)

    def test_warning_message(self):
        # The deletion view informs the user what will happen if they delete
        # the repository.
        repository = self.factory.makeGitRepository()
        name = repository.display_name
        text = self.getMainText(
            repository, "+delete", rootsite="code", user=repository.owner)
        self.assertThat(
            text, DocTestMatches(
                "Delete repository %s ...\n"
                "Repository deletion is permanent.\n"
                "or Cancel" % name,
                flags=(doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS)))

    def test_next_url(self):
        # Deleting a repository takes the user back to the code listing for
        # the target, and shows a notification message.
        project = self.factory.makeProduct()
        project_url = canonical_url(project, rootsite="code")
        repository = self.factory.makeGitRepository(target=project)
        name = repository.unique_name
        browser = self.getViewBrowser(
            repository, "+delete", rootsite="code", user=repository.owner)
        browser.getControl("Delete").click()
        self.assertEqual(project_url, browser.url)
        self.assertEqual(
            ["Repository %s deleted." % name],
            get_feedback_messages(browser.contents))

    def test_next_url_personal(self):
        # Deleting a personal repository takes the user back to the code
        # listing for the owner, and shows a notification message.
        owner = self.factory.makePerson()
        owner_url = canonical_url(owner, rootsite="code")
        repository = self.factory.makeGitRepository(owner=owner, target=owner)
        name = repository.unique_name
        browser = self.getViewBrowser(
            repository, "+delete", rootsite="code", user=repository.owner)
        browser.getControl("Delete").click()
        self.assertEqual(owner_url, browser.url)
        self.assertEqual(
            ["Repository %s deleted." % name],
            get_feedback_messages(browser.contents))
