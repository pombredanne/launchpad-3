# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for BranchView."""

__metaclass__ = type

from BeautifulSoup import BeautifulSoup
from datetime import (
    datetime,
    )
from textwrap import dedent

import pytz
from zope.publisher.interfaces import NotFound
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.launchpad.helpers import truncate_text
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from canonical.launchpad.testing.pages import (
    extract_text,
    find_tag_by_id,
    setupBrowser,
    setupBrowserForUser)
from lp.app.interfaces.headings import IRootContext
from lp.bugs.interfaces.bugtask import (
    BugTaskStatus,
    UNRESOLVED_BUGTASK_STATUSES,
    )
from lp.code.browser.branch import (
    BranchAddView,
    BranchMirrorStatusView,
    BranchReviewerEditView,
    BranchView,
    )
from lp.code.browser.branchlisting import PersonOwnedBranchesView
from lp.code.bzr import (
    BranchFormat,
    ControlFormat,
    RepositoryFormat,
    )
from lp.code.enums import (
    BranchLifecycleStatus,
    BranchType,
    BranchVisibilityRule,
    )
from lp.code.interfaces.branchtarget import IBranchTarget
from lp.registry.interfaces.person import PersonVisibility
from lp.testing import (
    BrowserTestCase,
    login,
    login_person,
    logout,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.matchers import (
    BrowsesWithQueryLimit,
    Contains,
    )
from lp.testing.views import create_initialized_view


class TestBranchMirrorHidden(TestCaseWithFactory):
    """Make sure that the appropriate mirror locations are hidden."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        config.push(
            "test", dedent("""\
                [codehosting]
                private_mirror_hosts: private.example.com
                """))

    def tearDown(self):
        config.pop("test")
        TestCaseWithFactory.tearDown(self)

    def testNormalBranch(self):
        # A branch from a normal location is fine.
        branch = self.factory.makeAnyBranch(
            branch_type=BranchType.MIRRORED,
            url="http://example.com/good/mirror")
        view = BranchView(branch, LaunchpadTestRequest())
        view.initialize()
        self.assertTrue(view.user is None)
        self.assertEqual(
            "http://example.com/good/mirror", view.mirror_location)

    def testLocationlessRemoteBranch(self):
        # A branch from a normal location is fine.
        branch = self.factory.makeAnyBranch(
            branch_type=BranchType.REMOTE,
            url=None)
        view = BranchView(branch, LaunchpadTestRequest())
        view.initialize()
        self.assertTrue(view.user is None)
        self.assertIs(None, view.mirror_location)

    def testHiddenBranchAsAnonymous(self):
        # A branch location with a defined private host is hidden from
        # anonymous browsers.
        branch = self.factory.makeAnyBranch(
            branch_type=BranchType.MIRRORED,
            url="http://private.example.com/bzr-mysql/mysql-5.0")
        view = BranchView(branch, LaunchpadTestRequest())
        view.initialize()
        self.assertTrue(view.user is None)
        self.assertEqual(
            "<private server>", view.mirror_location)

    def testHiddenBranchAsBranchOwner(self):
        # A branch location with a defined private host is visible to the
        # owner.
        owner = self.factory.makePerson(
            email="eric@example.com", password="test")
        branch = self.factory.makeAnyBranch(
            branch_type=BranchType.MIRRORED,
            owner=owner,
            url="http://private.example.com/bzr-mysql/mysql-5.0")
        # Now log in the owner.
        logout()
        login('eric@example.com')
        view = BranchView(branch, LaunchpadTestRequest())
        view.initialize()
        self.assertEqual(view.user, owner)
        self.assertEqual(
            "http://private.example.com/bzr-mysql/mysql-5.0",
            view.mirror_location)

    def testHiddenBranchAsOtherLoggedInUser(self):
        # A branch location with a defined private host is hidden from other
        # users.
        owner = self.factory.makePerson(
            email="eric@example.com", password="test")
        other = self.factory.makePerson(
            email="other@example.com", password="test")
        branch = self.factory.makeAnyBranch(
            branch_type=BranchType.MIRRORED,
            owner=owner,
            url="http://private.example.com/bzr-mysql/mysql-5.0")
        # Now log in the other person.
        logout()
        login('other@example.com')
        view = BranchView(branch, LaunchpadTestRequest())
        view.initialize()
        self.assertEqual(view.user, other)
        self.assertEqual(
            "<private server>", view.mirror_location)


class TestBranchView(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBranchView, self).setUp()
        self.request = LaunchpadTestRequest()

    def testMirrorStatusMessageIsTruncated(self):
        """mirror_status_message is truncated if the text is overly long."""
        branch = self.factory.makeBranch(branch_type=BranchType.MIRRORED)
        branch.mirrorFailed(
            "on quick brown fox the dog jumps to" *
            BranchMirrorStatusView.MAXIMUM_STATUS_MESSAGE_LENGTH)
        branch_view = BranchMirrorStatusView(branch, self.request)
        self.assertEqual(
            truncate_text(branch.mirror_status_message,
                          branch_view.MAXIMUM_STATUS_MESSAGE_LENGTH) + ' ...',
            branch_view.mirror_status_message)

    def testMirrorStatusMessage(self):
        """mirror_status_message on the view is the same as on the branch."""
        branch = self.factory.makeBranch(branch_type=BranchType.MIRRORED)
        branch.mirrorFailed("This is a short error message.")
        branch_view = BranchMirrorStatusView(branch, self.request)
        self.assertTrue(
            len(branch.mirror_status_message)
            <= branch_view.MAXIMUM_STATUS_MESSAGE_LENGTH,
            "branch.mirror_status_message longer than expected: %r"
            % (branch.mirror_status_message, ))
        self.assertEqual(
            branch.mirror_status_message, branch_view.mirror_status_message)
        self.assertEqual(
            "This is a short error message.",
            branch_view.mirror_status_message)

    def testBranchAddRequests(self):
        """Registering a branch that requests a mirror."""
        arbitrary_person = self.factory.makePerson()
        arbitrary_product = self.factory.makeProduct()
        login_person(arbitrary_person)
        try:
            add_view = BranchAddView(arbitrary_person, self.request)
            add_view.initialize()
            data = {
                'branch_type': BranchType.HOSTED,
                'name': 'some-branch',
                'title': 'Branch Title',
                'summary': '',
                'lifecycle_status': BranchLifecycleStatus.DEVELOPMENT,
                'whiteboard': '',
                'owner': arbitrary_person,
                'author': arbitrary_person,
                'product': arbitrary_product,
                }
            add_view.add_action.success(data)
        finally:
            logout()

    def testShowMergeLinksOnManyBranchProject(self):
        # The merge links are shown on projects that have multiple branches.
        product = self.factory.makeProduct(name='super-awesome-project')
        branch1 = self.factory.makeAnyBranch(product=product)
        self.factory.makeAnyBranch(product=product)
        view = BranchView(branch1, self.request)
        view.initialize()
        self.assertTrue(view.show_merge_links)

    def testShowMergeLinksOnJunkBranch(self):
        # The merge links are not shown on junk branches because they do not
        # support merge proposals.
        junk_branch = self.factory.makeBranch(product=None)
        view = BranchView(junk_branch, self.request)
        view.initialize()
        self.assertFalse(view.show_merge_links)

    def testShowMergeLinksOnSingleBranchProject(self):
        # The merge links are not shown on branches attached to a project that
        # only has one branch because it's pointless to propose it for merging
        # if there's nothing to merge into.
        branch = self.factory.makeAnyBranch()
        view = BranchView(branch, self.request)
        view.initialize()
        self.assertFalse(view.show_merge_links)

    def testNoProductSeriesPushingTranslations(self):
        # By default, a branch view shows no product series pushing
        # translations to the branch.
        branch = self.factory.makeBranch()

        view = BranchView(branch, self.request)
        view.initialize()
        self.assertEqual(list(view.translations_sources()), [])

    def testProductSeriesPushingTranslations(self):
        # If a product series exports its translations to the branch,
        # the view shows it.
        product = self.factory.makeProduct()
        trunk = product.getSeries('trunk')
        branch = self.factory.makeBranch(owner=product.owner)
        removeSecurityProxy(trunk).translations_branch = branch

        view = BranchView(branch, self.request)
        view.initialize()
        self.assertEqual(list(view.translations_sources()), [trunk])

    def test_is_empty_directory(self):
        # Branches are considered empty until they get a control format.
        branch = self.factory.makeBranch()
        view = BranchView(branch, self.request)
        view.initialize()
        self.assertTrue(view.is_empty_directory)
        with person_logged_in(branch.owner):
            # Make it look as though the branch has been pushed.
            branch.branchChanged(
                None, None, ControlFormat.BZR_METADIR_1, None, None)
        self.assertFalse(view.is_empty_directory)

    def test_empty_directories_use_existing(self):
        # Push example should include --use-existing for empty directories.
        branch = self.factory.makeBranch(owner=self.user)
        text = self.getMainText(branch)
        self.assertIn('push\n--use-existing', text)
        with person_logged_in(self.user):
            # Make it look as though the branch has been pushed.
            branch.branchChanged(
                None, None, ControlFormat.BZR_METADIR_1, None, None)
        text = self.getMainText(branch)
        self.assertNotIn('push\n--use-existing', text)

    def test_user_can_upload(self):
        # A user can upload if they have edit permissions.
        branch = self.factory.makeAnyBranch()
        view = create_initialized_view(branch, '+index')
        login_person(branch.owner)
        self.assertTrue(view.user_can_upload)

    def test_user_can_upload_admins_can(self):
        # Admins can upload to any hosted branch.
        branch = self.factory.makeAnyBranch()
        view = create_initialized_view(branch, '+index')
        login('admin@canonical.com')
        self.assertTrue(view.user_can_upload)

    def test_user_can_upload_non_owner(self):
        # Someone not associated with the branch cannot upload
        branch = self.factory.makeAnyBranch()
        view = create_initialized_view(branch, '+index')
        login_person(self.factory.makePerson())
        self.assertFalse(view.user_can_upload)

    def test_user_can_upload_mirrored(self):
        # Even the owner of a mirrored branch can't upload.
        branch = self.factory.makeAnyBranch(branch_type=BranchType.MIRRORED)
        view = create_initialized_view(branch, '+index')
        login_person(branch.owner)
        self.assertFalse(view.user_can_upload)

    def _addBugLinks(self, branch):
        for status in BugTaskStatus.items:
            bug = self.factory.makeBug(status=status)
            branch.linkBug(bug, branch.owner)

    def test_linked_bugtasks(self):
        # The linked bugs for a non series branch shows all linked bugs.
        branch = self.factory.makeAnyBranch()
        with person_logged_in(branch.owner):
            self._addBugLinks(branch)
        view = create_initialized_view(branch, '+index')
        self.assertEqual(len(BugTaskStatus), len(view.linked_bugtasks))
        self.assertFalse(view.context.is_series_branch)

    def test_linked_bugtasks_privacy(self):
        # If a linked bug is private, it is not in the linked bugs if the user
        # can't see any of the tasks.
        branch = self.factory.makeAnyBranch()
        reporter = self.factory.makePerson()
        bug = self.factory.makeBug(private=True, owner=reporter)
        with person_logged_in(reporter):
            branch.linkBug(bug, reporter)
            view = create_initialized_view(branch, '+index')
            self.assertEqual([bug.id],
                [task.bug.id for task in view.linked_bugtasks])
        with person_logged_in(branch.owner):
            view = create_initialized_view(branch, '+index')
            self.assertEqual([], view.linked_bugtasks)

    def test_linked_bugtasks_series_branch(self):
        # The linked bugtasks for a series branch shows only unresolved bugs.
        product = self.factory.makeProduct()
        branch = self.factory.makeProductBranch(product=product)
        with person_logged_in(product.owner):
            product.development_focus.branch = branch
        with person_logged_in(branch.owner):
            self._addBugLinks(branch)
        view = create_initialized_view(branch, '+index')
        for bugtask in view.linked_bugtasks:
            self.assertTrue(
                bugtask.status in UNRESOLVED_BUGTASK_STATUSES)

    # XXX wgrant 2011-10-21 bug=879197: Disabled due to spurious failure.
    def disabled_test_linked_bugs_nonseries_branch_query_scaling(self):
        # As we add linked bugs, the query count for a branch index page stays
        # constant.
        branch = self.factory.makeAnyBranch()
        browses_under_limit = BrowsesWithQueryLimit(54, branch.owner)
        # Start with some bugs, otherwise we might see a spurious increase
        # depending on optimisations in eager loaders.
        with person_logged_in(branch.owner):
            self._addBugLinks(branch)
            self.assertThat(branch, browses_under_limit)
        with person_logged_in(branch.owner):
            # Add plenty of bugs.
            for _ in range(5):
                self._addBugLinks(branch)
            self.assertThat(branch, browses_under_limit)

    def test_linked_bugs_series_branch_query_scaling(self):
        # As we add linked bugs, the query count for a branch index page stays
        # constant.
        product = self.factory.makeProduct()
        branch = self.factory.makeProductBranch(product=product)
        browses_under_limit = BrowsesWithQueryLimit(54, branch.owner)
        with person_logged_in(product.owner):
            product.development_focus.branch = branch
        # Start with some bugs, otherwise we might see a spurious increase
        # depending on optimisations in eager loaders.
        with person_logged_in(branch.owner):
            self._addBugLinks(branch)
            self.assertThat(branch, browses_under_limit)
        with person_logged_in(branch.owner):
            # Add plenty of bugs.
            for _ in range(5):
                self._addBugLinks(branch)
            self.assertThat(branch, browses_under_limit)

    def _add_revisions(self, branch, nr_revisions=1):
        revisions = []
        for seq in range(1, nr_revisions + 1):
            revision = self.factory.makeRevision(
                author="Eric the Viking <eric@vikings-r-us.example.com>",
                log_body=(
                    "Testing the email address in revisions\n"
                    "email Bob (bob@example.com) for details."))

            branch_revision = branch.createBranchRevision(seq, revision)
            branch.updateScannedDetails(revision, seq)
            revisions.append(branch_revision)
        return revisions

    def test_recent_revisions(self):
        # There is a heading for the recent revisions.
        branch = self.factory.makeAnyBranch()
        with person_logged_in(branch.owner):
            self._add_revisions(branch)
        browser = self.getUserBrowser(canonical_url(branch))
        tag = find_tag_by_id(browser.contents, 'recent-revisions')
        text = extract_text(tag)
        expected_text = """
            Recent revisions
            .*
            1. By Eric the Viking &lt;eric@vikings-r-us.example.com&gt;
            .*
            Testing the email address in revisions\n
            email Bob \(bob@example.com\) for details.
            """

        self.assertTextMatchesExpressionIgnoreWhitespace(expected_text, text)

    def test_recent_revisions_email_hidden_with_no_login(self):
        # If the user is not logged in, the email addresses are hidden in both
        # the revision author and the commit message.
        branch = self.factory.makeAnyBranch()
        with person_logged_in(branch.owner):
            self._add_revisions(branch)
            branch_url = canonical_url(branch)
        browser = setupBrowser()
        logout()
        browser.open(branch_url)
        tag = find_tag_by_id(browser.contents, 'recent-revisions')
        text = extract_text(tag)
        expected_text = """
            Recent revisions
            .*
            1. By Eric the Viking &lt;email address hidden&gt;
            .*
            Testing the email address in revisions\n
            email Bob \(&lt;email address hidden&gt;\) for details.
            """
        self.assertTextMatchesExpressionIgnoreWhitespace(expected_text, text)

    def test_recent_revisions_with_merge_proposals(self):
        # Revisions which result from merging in a branch with a merge
        # proposal show the merge proposal details.

        branch = self.factory.makeAnyBranch()
        with person_logged_in(branch.owner):
            revisions = self._add_revisions(branch, 2)
            mp = self.factory.makeBranchMergeProposal(
                target_branch=branch, registrant=branch.owner)
            mp.markAsMerged(merged_revno=revisions[0].sequence)

            # These values are extracted here and used below.
            mp_url = canonical_url(mp, rootsite='code', force_local_path=True)
            branch_display_name = mp.source_branch.displayname

        browser = self.getUserBrowser(canonical_url(branch))

        revision_content = find_tag_by_id(
            browser.contents, 'recent-revisions')

        text = extract_text(revision_content)
        expected_text = """
            Recent revisions
            .*
            2. By Eric the Viking &lt;eric@vikings-r-us.example.com&gt;
            .*
            Testing the email address in revisions\n
            email Bob \(bob@example.com\) for details.\n
            1. By Eric the Viking &lt;eric@vikings-r-us.example.com&gt;
            .*
            Testing the email address in revisions\n
            email Bob \(bob@example.com\) for details.
            Merged branch %s
            """ % branch_display_name

        self.assertTextMatchesExpressionIgnoreWhitespace(expected_text, text)

        links = revision_content.findAll('a')
        self.assertEqual(mp_url, links[2]['href'])

    def test_recent_revisions_with_merge_proposals_and_bug_links(self):
        # Revisions which result from merging in a branch with a merge
        # proposal show the merge proposal details. If the source branch of
        # the merge proposal has linked bugs, these should also be shown.

        branch = self.factory.makeAnyBranch()
        with person_logged_in(branch.owner):
            revisions = self._add_revisions(branch, 2)
            mp = self.factory.makeBranchMergeProposal(
                target_branch=branch, registrant=branch.owner)
            mp.markAsMerged(merged_revno=revisions[0].sequence)

            # record linked bug info for use below
            linked_bug_urls = []
            linked_bug_text = []
            for x in range(0, 2):
                bug = self.factory.makeBug()
                mp.source_branch.linkBug(bug, branch.owner)
                linked_bug_urls.append(
                    canonical_url(bug.default_bugtask, rootsite='bugs'))
                bug_text = "Bug #%s: %s" % (bug.id, bug.title)
                linked_bug_text.append(bug_text)

            # These values are extracted here and used below.
            linked_bug_rendered_text = "\n".join(linked_bug_text)
            mp_url = canonical_url(mp, force_local_path=True)
            branch_display_name = mp.source_branch.displayname

        browser = self.getUserBrowser(canonical_url(branch))

        revision_content = find_tag_by_id(
            browser.contents, 'recent-revisions')

        text = extract_text(revision_content)
        expected_text = """
            Recent revisions
            .*
            2. By Eric the Viking &lt;eric@vikings-r-us.example.com&gt;
            .*
            Testing the email address in revisions\n
            email Bob \(bob@example.com\) for details.\n
            1. By Eric the Viking &lt;eric@vikings-r-us.example.com&gt;
            .*
            Testing the email address in revisions\n
            email Bob \(bob@example.com\) for details.
            Merged branch %s
            %s
            """ % (branch_display_name, linked_bug_rendered_text)

        self.assertTextMatchesExpressionIgnoreWhitespace(expected_text, text)

        links = revision_content.findAll('a')
        self.assertEqual(mp_url, links[2]['href'])
        self.assertEqual(linked_bug_urls[0], links[3]['href'])
        self.assertEqual(linked_bug_urls[1], links[4]['href'])


class TestBranchViewPrivateArtifacts(BrowserTestCase):
    """ Tests that branches with private team artifacts can be viewed.

    A Branch may be associated with a private team as follows:
    - the owner
    - a subscriber
    - committed a revision
    - be a code reviewer

    A logged in user who is not authorised to see the private team(s) still
    needs to be able to view the branch. The private team will be rendered in
    the normal way, displaying the team name and Launchpad URL.
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

    def test_aaaa(self):
        # A branch with a private owner is not rendered for anon users.
        private_owner = self.factory.makeTeam(
            visibility=PersonVisibility.PRIVATE)
        # Viewing the branch results in an error.
        url = canonical_url(removeSecurityProxy(private_owner))
        user = self.factory.makePerson()
        browser = self._getBrowser(user)
        self.assertRaises(NotFound, browser.open, url)

    def test_bbbb(self):
        # A branch with a private owner is not rendered for anon users.
        private_owner = self.factory.makeTeam(
            visibility=PersonVisibility.PRIVATE)
        branch = self.factory.makeAnyBranch(owner=private_owner)
        # Viewing the branch results in an error.
        url = canonical_url(branch, rootsite='code')
        browser = self._getBrowser()
        self.assertRaises(NotFound, browser.open, url)

    def test_view_branch_with_private_owner(self):
        # A branch with a private owner is rendered.
        private_owner = self.factory.makeTeam(
            displayname="PrivateTeam", visibility=PersonVisibility.PRIVATE)
        branch = self.factory.makeAnyBranch(owner=private_owner)
        # Ensure the branch owner is rendered.
        url = canonical_url(branch, rootsite='code')
        user = self.factory.makePerson()
        browser = self._getBrowser(user)
        browser.open(url)
        soup = BeautifulSoup(browser.contents)
        self.assertIsNotNone(soup.find('a', text="PrivateTeam"))

    def test_anonymous_view_branch_with_private_owner(self):
        # A branch with a private owner is not rendered for anon users.
        private_owner = self.factory.makeTeam(
            visibility=PersonVisibility.PRIVATE)
        branch = self.factory.makeAnyBranch(owner=private_owner)
        # Viewing the branch results in an error.
        url = canonical_url(branch, rootsite='code')
        browser = self._getBrowser()
        self.assertRaises(NotFound, browser.open, url)

    def test_view_branch_with_private_subscriber(self):
        # A branch with a private subscriber is rendered.
        private_subscriber = self.factory.makeTeam(
            name="privateteam", visibility=PersonVisibility.PRIVATE)
        branch = self.factory.makeAnyBranch()
        with person_logged_in(branch.owner):
            self.factory.makeBranchSubscription(
                branch, private_subscriber, branch.owner)
        # Ensure the branch subscriber is rendered.
        url = canonical_url(branch, rootsite='code')
        user = self.factory.makePerson()
        browser = self._getBrowser(user)
        browser.open(url)
        soup = BeautifulSoup(browser.contents)
        self.assertIsNotNone(
            soup.find('div', attrs={'id': 'subscriber-privateteam'}))

    def test_anonymous_view_branch_with_private_subscriber(self):
        # A branch with a private subscriber is not rendered for anon users.
        private_subscriber = self.factory.makeTeam(
            name="privateteam", visibility=PersonVisibility.PRIVATE)
        branch = self.factory.makeAnyBranch()
        with person_logged_in(branch.owner):
            self.factory.makeBranchSubscription(
                branch, private_subscriber, branch.owner)
        # Viewing the branch results in an error.
        url = canonical_url(branch, rootsite='code')
        browser = self._getBrowser()
        browser.open(url)
        soup = BeautifulSoup(browser.contents)
        self.assertIsNone(
            soup.find('div', attrs={'id': 'subscriber-privateteam'}))

    def test_view_branch_with_private_reviewer(self):
        # A branch with a private reviewer is rendered.
        private_reviewer = self.factory.makeTeam(
            displayname="PrivateTeam", visibility=PersonVisibility.PRIVATE)
        branch = self.factory.makeAnyBranch()
        with person_logged_in(branch.owner):
            self.factory.makeBranchMergeProposal(
                source_branch=branch, reviewer=private_reviewer)
        # Ensure the branch reviewer is rendered.
        url = canonical_url(branch, rootsite='code')
        user = self.factory.makePerson()
        browser = self._getBrowser(user)
        browser.open(url)
        soup = BeautifulSoup(browser.contents)
        self.assertIsNotNone(
            soup.find('a', text="PrivateTeam"))

    def test_anonymous_view_branch_with_private_reviewer(self):
        # A branch with a private reviewer is not rendered for anon users.
        private_reviewer = self.factory.makeTeam(
            visibility=PersonVisibility.PRIVATE)
        branch = self.factory.makeAnyBranch()
        with person_logged_in(branch.owner):
            self.factory.makeBranchMergeProposal(
                source_branch=branch, reviewer=private_reviewer)
        # Viewing the branch results in an error.
        url = canonical_url(branch, rootsite='code')
        browser = self._getBrowser()
        self.assertRaises(NotFound, browser.open, url)


class TestBranchAddView(TestCaseWithFactory):
    """Test the BranchAddView view."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBranchAddView, self).setUp()
        self.person = self.factory.makePerson()
        login_person(self.person)
        self.request = LaunchpadTestRequest()

    def tearDown(self):
        logout()
        super(TestBranchAddView, self).tearDown()

    def get_view(self, context):
        view = BranchAddView(context, self.request)
        view.initialize()
        return view

    def test_target_person(self):
        add_view = self.get_view(self.person)
        self.assertTrue(IBranchTarget.providedBy(add_view.target))

    def test_target_product(self):
        product = self.factory.makeProduct()
        add_view = self.get_view(product)
        self.assertTrue(IBranchTarget.providedBy(add_view.target))


class TestBranchReviewerEditView(TestCaseWithFactory):
    """Test the BranchReviewerEditView view."""

    layer = DatabaseFunctionalLayer

    def test_initial_reviewer_not_set(self):
        # If the reviewer is not set, the field is populated with the owner of
        # the branch.
        branch = self.factory.makeAnyBranch()
        self.assertIs(None, branch.reviewer)
        view = BranchReviewerEditView(branch, LaunchpadTestRequest())
        self.assertEqual(
            branch.owner,
            view.initial_values['reviewer'])

    def test_initial_reviewer_set(self):
        # If the reviewer has been set, it is shown as the initial value.
        branch = self.factory.makeAnyBranch()
        login_person(branch.owner)
        branch.reviewer = self.factory.makePerson()
        view = BranchReviewerEditView(branch, LaunchpadTestRequest())
        self.assertEqual(
            branch.reviewer,
            view.initial_values['reviewer'])

    def test_set_reviewer(self):
        # Test setting the reviewer.
        branch = self.factory.makeAnyBranch()
        reviewer = self.factory.makePerson()
        login_person(branch.owner)
        view = BranchReviewerEditView(branch, LaunchpadTestRequest())
        view.initialize()
        view.change_action.success({'reviewer': reviewer})
        self.assertEqual(reviewer, branch.reviewer)
        # Last modified has been updated.
        self.assertSqlAttributeEqualsDate(
            branch, 'date_last_modified', UTC_NOW)

    def test_set_reviewer_as_owner_clears_reviewer(self):
        # If the reviewer is set to be the branch owner, the review field is
        # cleared in the database.
        branch = self.factory.makeAnyBranch()
        login_person(branch.owner)
        branch.reviewer = self.factory.makePerson()
        view = BranchReviewerEditView(branch, LaunchpadTestRequest())
        view.initialize()
        view.change_action.success({'reviewer': branch.owner})
        self.assertIs(None, branch.reviewer)
        # Last modified has been updated.
        self.assertSqlAttributeEqualsDate(
            branch, 'date_last_modified', UTC_NOW)

    def test_set_reviewer_to_same_does_not_update_last_modified(self):
        # If the user has set the reviewer to be same and clicked on save,
        # then the underlying object hasn't really been changed, so the last
        # modified is not updated.
        modified_date = datetime(2007, 1, 1, tzinfo=pytz.UTC)
        branch = self.factory.makeAnyBranch(date_created=modified_date)
        view = BranchReviewerEditView(branch, LaunchpadTestRequest())
        view.initialize()
        view.change_action.success({'reviewer': branch.owner})
        self.assertIs(None, branch.reviewer)
        # Last modified has not been updated.
        self.assertEqual(modified_date, branch.date_last_modified)


class TestBranchBzrIdentity(TestCaseWithFactory):
    """Test the bzr_identity on the PersonOwnedBranchesView."""

    layer = DatabaseFunctionalLayer

    def test_dev_focus_identity(self):
        # A branch that is a development focus branch, should show using the
        # short name on the listing.
        product = self.factory.makeProduct(name="fooix")
        branch = self.factory.makeProductBranch(product=product)
        # To avoid dealing with admins, just log in the product owner to set
        # the development focus branch.
        login_person(product.owner)
        product.development_focus.branch = branch
        view = PersonOwnedBranchesView(branch.owner, LaunchpadTestRequest())
        view.initialize()
        navigator = view.branches()
        [decorated_branch] = navigator.branches
        self.assertEqual("lp://dev/fooix", decorated_branch.bzr_identity)


class TestBranchProposalsVisible(TestCaseWithFactory):
    """Test that the BranchView filters out proposals the user cannot see."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)

    def test_public_target(self):
        # If the user can see the target, then there are merges, and the
        # landing_target is available for the template rendering.
        bmp = self.factory.makeBranchMergeProposal()
        branch = bmp.source_branch
        view = BranchView(branch, LaunchpadTestRequest())
        self.assertFalse(view.no_merges)
        [target] = view.landing_targets
        # Check the ids as the target is a DecoratedMergeProposal.
        self.assertEqual(bmp.id, target.id)

    def test_private_target(self):
        # If the target is private, the landing targets should not include it.
        bmp = self.factory.makeBranchMergeProposal()
        branch = bmp.source_branch
        removeSecurityProxy(bmp.target_branch).explicitly_private = True
        view = BranchView(branch, LaunchpadTestRequest())
        self.assertTrue(view.no_merges)
        self.assertEqual([], view.landing_targets)

    def test_public_source(self):
        # If the user can see the source, then there are merges, and the
        # landing_candidate is available for the template rendering.
        bmp = self.factory.makeBranchMergeProposal()
        branch = bmp.target_branch
        view = BranchView(branch, LaunchpadTestRequest())
        self.assertFalse(view.no_merges)
        [candidate] = view.landing_candidates
        # Check the ids as the target is a DecoratedMergeProposal.
        self.assertEqual(bmp.id, candidate.id)

    def test_private_source(self):
        # If the source is private, the landing candidates should not include
        # it.
        bmp = self.factory.makeBranchMergeProposal()
        branch = bmp.target_branch
        removeSecurityProxy(bmp.source_branch).explicitly_private = True
        view = BranchView(branch, LaunchpadTestRequest())
        self.assertTrue(view.no_merges)
        self.assertEqual([], view.landing_candidates)

    def test_prerequisite_public(self):
        # If the branch is a prerequisite branch for a public proposals, then
        # there are merges.
        branch = self.factory.makeProductBranch()
        bmp = self.factory.makeBranchMergeProposal(prerequisite_branch=branch)
        view = BranchView(branch, LaunchpadTestRequest())
        self.assertFalse(view.no_merges)
        [proposal] = view.dependent_branches
        self.assertEqual(bmp, proposal)

    def test_prerequisite_private(self):
        # If the branch is a prerequisite branch where either the source or
        # the target is private, then the dependent_branches are not shown.
        branch = self.factory.makeProductBranch()
        bmp = self.factory.makeBranchMergeProposal(prerequisite_branch=branch)
        removeSecurityProxy(bmp.source_branch).explicitly_private = True
        view = BranchView(branch, LaunchpadTestRequest())
        self.assertTrue(view.no_merges)
        self.assertEqual([], view.dependent_branches)


class TestBranchRootContext(TestCaseWithFactory):
    """Test the adaptation of IBranch to IRootContext."""

    layer = DatabaseFunctionalLayer

    def test_personal_branch(self):
        # The root context of a personal branch is the person.
        branch = self.factory.makePersonalBranch()
        root_context = IRootContext(branch)
        self.assertEqual(branch.owner, root_context)

    def test_package_branch(self):
        # The root context of a package branch is the distribution.
        branch = self.factory.makePackageBranch()
        root_context = IRootContext(branch)
        self.assertEqual(branch.distroseries.distribution, root_context)

    def test_product_branch(self):
        # The root context of a product branch is the product.
        branch = self.factory.makeProductBranch()
        root_context = IRootContext(branch)
        self.assertEqual(branch.product, root_context)


class TestBranchEditView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_allowed_owner_is_ok(self):
        # A branch's owner can be changed to a team permitted by the
        # visibility policy.
        person = self.factory.makePerson()
        branch = self.factory.makeProductBranch(owner=person)
        team = self.factory.makeTeam(
            owner=person, displayname="Permitted team")
        branch.product.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.FORBIDDEN)
        branch.product.setBranchVisibilityTeamPolicy(
            team, BranchVisibilityRule.PRIVATE)
        browser = self.getUserBrowser(
            canonical_url(branch) + '/+edit', user=person)
        browser.getControl("Owner").displayValue = ["Permitted team"]
        browser.getControl("Change Branch").click()
        with person_logged_in(person):
            self.assertEquals(team, branch.owner)

    def test_forbidden_owner_is_error(self):
        # An error is displayed if a branch's owner is changed to
        # a value forbidden by the visibility policy.
        product = self.factory.makeProduct(displayname='Some Product')
        person = self.factory.makePerson()
        branch = self.factory.makeBranch(product=product, owner=person)
        self.factory.makeTeam(
            owner=person, displayname="Forbidden team")
        branch.product.setBranchVisibilityTeamPolicy(
            None, BranchVisibilityRule.FORBIDDEN)
        branch.product.setBranchVisibilityTeamPolicy(
            person, BranchVisibilityRule.PRIVATE)
        browser = self.getUserBrowser(
            canonical_url(branch) + '/+edit', user=person)
        browser.getControl("Owner").displayValue = ["Forbidden team"]
        browser.getControl("Change Branch").click()
        self.assertThat(
            browser.contents,
            Contains(
                'Forbidden team is not allowed to own branches in '
                'Some Product.'))
        with person_logged_in(person):
            self.assertEquals(person, branch.owner)


class TestBranchUpgradeView(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_upgrade_branch_action_cannot_upgrade(self):
        # A nice error is displayed if a branch cannot be upgraded.
        branch = self.factory.makePersonalBranch(
        branch_format=BranchFormat.BZR_BRANCH_6,
        repository_format=RepositoryFormat.BZR_CHK_2A)
        login_person(branch.owner)
        self.addCleanup(logout)
        branch.requestUpgrade(branch.owner)
        view = create_initialized_view(branch, '+upgrade')
        view.upgrade_branch_action.success({})
        self.assertEqual(1, len(view.request.notifications))
        self.assertEqual(
            'An upgrade is already in progress for branch %s.' %
            branch.bzr_identity, view.request.notifications[0].message)
