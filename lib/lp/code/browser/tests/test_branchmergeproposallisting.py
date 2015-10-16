# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for BranchMergeProposal listing views."""

__metaclass__ = type

from datetime import datetime

import pytz
from testtools.content import Content
from testtools.content_type import UTF8_TEXT
from testtools.matchers import LessThan
import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.app.enums import InformationType
from lp.app.interfaces.services import IService
from lp.code.browser.branchmergeproposallisting import (
    ActiveReviewsView,
    BranchMergeProposalListingItem,
    )
from lp.code.enums import (
    BranchMergeProposalStatus,
    CodeReviewVote,
    )
from lp.code.interfaces.gitref import IGitRef
from lp.code.interfaces.gitrepository import IGitRepositorySet
from lp.registry.enums import SharingPermission
from lp.registry.model.personproduct import PersonProduct
from lp.services.database.sqlbase import flush_database_caches
from lp.services.webapp.publisher import canonical_url
from lp.testing import (
    admin_logged_in,
    ANONYMOUS,
    BrowserTestCase,
    login,
    login_person,
    person_logged_in,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing.matchers import HasQueryCount
from lp.testing.views import create_initialized_view


_default = object()


class BzrMixin:
    """Mixin for Bazaar-based tests."""

    def _makeBranch(self, target=None, **kwargs):
        if target is not None:
            # This only handles projects at the moment.
            kwargs["product"] = target
        return self.factory.makeBranch(**kwargs)

    def _makePackageBranch(self, **kwargs):
        return self.factory.makePackageBranch(**kwargs)

    def _makeStackedOnBranchChain(self, target=None, **kwargs):
        if target is not None:
            # This only handles projects at the moment.
            kwargs["product"] = target
        return self.factory.makeStackedOnBranchChain(**kwargs)

    def _makeBranchMergeProposal(self, target=None, merge_target=None,
                                 **kwargs):
        # This only handles projects at the moment.
        return self.factory.makeBranchMergeProposal(
            product=target, target_branch=merge_target, **kwargs)


class GitMixin:
    """Mixin for Git-based tests."""

    def _makeBranch(self, **kwargs):
        return self.factory.makeGitRefs(**kwargs)[0]

    def _makePackageBranch(self, **kwargs):
        dsp = self.factory.makeDistributionSourcePackage()
        return self.factory.makeGitRefs(target=dsp, **kwargs)[0]

    def _makeStackedOnBranchChain(self, depth=None, **kwargs):
        # Git doesn't have stacked branches.  Just make an ordinary reference.
        return self._makeBranch(**kwargs)

    def _makeBranchMergeProposal(self, merge_target=None, **kwargs):
        return self.factory.makeBranchMergeProposalForGit(
            target_ref=merge_target, **kwargs)


class TestProposalVoteSummaryMixin:
    """The vote summary shows a summary of the current votes."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Use an admin so we don't have to worry about launchpad.Edit
        # permissions on the merge proposals for adding comments.
        super(TestProposalVoteSummaryMixin, self).setUp(
            user="admin@canonical.com")

    def _createComment(self, proposal, reviewer=None, vote=None,
                       comment=_default):
        """Create a comment on the merge proposal."""
        if reviewer is None:
            reviewer = self.factory.makePerson()
        if comment is _default:
            comment = self.factory.getUniqueString()
        proposal.createComment(
            owner=reviewer, subject=self.factory.getUniqueString('subject'),
            content=comment, vote=vote)

    def _get_vote_summary(self, proposal):
        """Return the vote summary string for the proposal."""
        view = create_initialized_view(
            proposal.merge_source.owner, '+merges', rootsite='code')
        batch_navigator = view.proposals
        # There will only be one item in the list of proposals.
        [listing_item] = batch_navigator.proposals
        return (list(listing_item.vote_summary_items),
                listing_item.comment_count)

    def test_no_votes_or_comments(self):
        # If there are no votes or comments, then we show that.
        proposal = self._makeBranchMergeProposal()
        summary, comment_count = self._get_vote_summary(proposal)
        self.assertEqual([], summary)
        self.assertEqual(0, comment_count)

    def test_no_votes_with_comments(self):
        # The comment count is shown.
        proposal = self._makeBranchMergeProposal()
        self._createComment(proposal)
        summary, comment_count = self._get_vote_summary(proposal)
        self.assertEqual([], summary)
        self.assertEqual(1, comment_count)

    def test_vote_without_comment(self):
        # If there are no comments we don't show a count.
        proposal = self._makeBranchMergeProposal()
        self._createComment(
            proposal, vote=CodeReviewVote.APPROVE, comment=None)
        summary, comment_count = self._get_vote_summary(proposal)
        self.assertEqual(
            [{'name': 'APPROVE', 'title':'Approve', 'count':1,
              'reviewers': ''}], summary)
        self.assertEqual(0, comment_count)

    def test_vote_with_comment(self):
        # A vote with a comment counts as a vote and a comment.
        proposal = self._makeBranchMergeProposal()
        self._createComment(proposal, vote=CodeReviewVote.APPROVE)
        summary, comment_count = self._get_vote_summary(proposal)
        self.assertEqual(
            [{'name': 'APPROVE', 'title':'Approve', 'count':1,
              'reviewers': ''}], summary)
        self.assertEqual(1, comment_count)

    def test_disapproval(self):
        # Shown as Disapprove: <count>.
        proposal = self._makeBranchMergeProposal()
        self._createComment(proposal, vote=CodeReviewVote.DISAPPROVE)
        summary, comment_count = self._get_vote_summary(proposal)
        self.assertEqual(
            [{'name': 'DISAPPROVE', 'title':'Disapprove', 'count':1,
              'reviewers': ''}], summary)
        self.assertEqual(1, comment_count)

    def test_abstain(self):
        # Shown as Abstain: <count>.
        proposal = self._makeBranchMergeProposal()
        transaction.commit()
        self._createComment(proposal, vote=CodeReviewVote.ABSTAIN)
        summary, comment_count = self._get_vote_summary(proposal)
        self.assertEqual(
            [{'name': 'ABSTAIN', 'title':'Abstain', 'count':1,
              'reviewers': ''}], summary)
        self.assertEqual(1, comment_count)

    def test_vote_ranking(self):
        # Votes go from best to worst.
        proposal = self._makeBranchMergeProposal()
        self._createComment(proposal, vote=CodeReviewVote.DISAPPROVE)
        self._createComment(proposal, vote=CodeReviewVote.APPROVE)
        summary, comment_count = self._get_vote_summary(proposal)
        self.assertEqual(
            [{'name': 'APPROVE', 'title':'Approve', 'count':1,
              'reviewers': ''},
             {'name': 'DISAPPROVE', 'title':'Disapprove', 'count':1,
              'reviewers': ''}], summary)
        self.assertEqual(2, comment_count)
        self._createComment(proposal, vote=CodeReviewVote.ABSTAIN)
        summary, comment_count = self._get_vote_summary(proposal)
        self.assertEqual(
            [{'name': 'APPROVE', 'title':'Approve', 'count':1,
              'reviewers': ''},
             {'name': 'ABSTAIN', 'title':'Abstain', 'count':1,
              'reviewers': ''},
             {'name': 'DISAPPROVE', 'title':'Disapprove', 'count':1,
              'reviewers': ''}], summary)
        self.assertEqual(3, comment_count)

    def test_multiple_votes_for_type(self):
        # Multiple votes of a type are aggregated in the summary.
        proposal = self._makeBranchMergeProposal()
        self._createComment(proposal, vote=CodeReviewVote.DISAPPROVE)
        self._createComment(proposal, vote=CodeReviewVote.APPROVE)
        self._createComment(proposal, vote=CodeReviewVote.DISAPPROVE)
        self._createComment(proposal, vote=CodeReviewVote.APPROVE)
        self._createComment(
            proposal, vote=CodeReviewVote.ABSTAIN, comment=None)
        self._createComment(
            proposal, vote=CodeReviewVote.APPROVE, comment=None)
        summary, comment_count = self._get_vote_summary(proposal)
        self.assertEqual(
            [{'name': 'APPROVE', 'title':'Approve', 'count':3,
              'reviewers': ''},
             {'name': 'ABSTAIN', 'title':'Abstain', 'count':1,
              'reviewers': ''},
             {'name': 'DISAPPROVE', 'title':'Disapprove', 'count':2,
              'reviewers': ''}], summary)
        self.assertEqual(4, comment_count)


class TestProposalVoteSummaryBzr(
    TestProposalVoteSummaryMixin, BzrMixin, TestCaseWithFactory):
    """Test the vote summary for Bazaar."""


class TestProposalVoteSummaryGit(
    TestProposalVoteSummaryMixin, GitMixin, TestCaseWithFactory):
    """Test the vote summary for Git."""


class TestMergesOnce(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def test_productseries_bzr(self):
        target = self.factory.makeBranch()
        with person_logged_in(target.product.owner):
            target.product.development_focus.branch = target
            identity = target.identity
        self.factory.makeBranchMergeProposal(target_branch=target)
        view = self.getViewBrowser(target, '+merges', rootsite='code')
        self.assertIn(identity, view.contents)

    def test_product_git(self):
        [target] = self.factory.makeGitRefs()
        with person_logged_in(target.target.owner):
            getUtility(IGitRepositorySet).setDefaultRepository(
                target.target, target.repository)
            identity = target.identity
        self.factory.makeBranchMergeProposalForGit(target_ref=target)
        view = self.getViewBrowser(target, '+merges', rootsite='code')
        self.assertIn(identity, view.contents)


class BranchMergeProposalListingTestMixin:

    layer = DatabaseFunctionalLayer

    supports_privacy = True
    supports_git = True
    supports_bzr = True
    label_describes_context = True

    bzr_branch = None
    git_ref = None

    def makeBzrMergeProposal(self):
        information_type = (
            InformationType.USERDATA if self.supports_privacy else None)
        target = self.bzr_branch
        if target is None:
            target = self.factory.makeBranch(
                target=self.bzr_target, information_type=information_type)
        source = self.factory.makeBranch(
            target=self.bzr_target, owner=self.owner,
            information_type=information_type)
        return self.factory.makeBranchMergeProposal(
            source_branch=source, target_branch=target,
            set_state=BranchMergeProposalStatus.NEEDS_REVIEW)

    def makeGitMergeProposal(self):
        information_type = (
            InformationType.USERDATA if self.supports_privacy else None)
        target = self.git_ref
        if target is None:
            [target] = self.factory.makeGitRefs(
                target=self.git_target, information_type=information_type)
        [source] = self.factory.makeGitRefs(
            target=self.git_target, owner=self.owner,
            information_type=information_type)
        return self.factory.makeBranchMergeProposalForGit(
            source_ref=source, target_ref=target,
            set_state=BranchMergeProposalStatus.NEEDS_REVIEW)

    def getExpectedLabel(self):
        if self.label_describes_context:
            return "%s for %s" % (self.page_title, self.context.displayname)
        else:
            return self.page_title

    def test_bzr(self):
        """The merges view should be enabled for the target."""
        if not self.supports_bzr:
            self.skipTest("Context doesn't support Bazaar branches.")
        with admin_logged_in():
            bmp = self.makeBzrMergeProposal()
            url = canonical_url(bmp, force_local_path=True)
            label = self.getExpectedLabel()
        browser = self.getViewBrowser(
            self.context, self.view_name, rootsite='code', user=self.user)
        self.assertIn(label, browser.contents)
        self.assertIn(url, browser.contents)

    def test_git(self):
        """The merges view should be enabled for the target."""
        if not self.supports_git:
            self.skipTest("Context doesn't support Git repositories.")
        with admin_logged_in():
            bmp = self.makeGitMergeProposal()
            url = canonical_url(bmp, force_local_path=True)
            label = self.getExpectedLabel()
        browser = self.getViewBrowser(
            self.context, self.view_name, rootsite='code', user=self.user)
        self.assertIn(label, browser.contents)
        self.assertIn(url, browser.contents)

    def test_query_count_bzr(self):
        if not self.supports_bzr:
            self.skipTest("Context doesn't support Bazaar branches.")
        with admin_logged_in():
            for i in range(7):
                self.makeBzrMergeProposal()
        flush_database_caches()
        with StormStatementRecorder() as recorder:
            self.getViewBrowser(
                self.context, self.view_name, rootsite='code', user=self.user)
        self.assertThat(recorder, HasQueryCount(LessThan(51)))

    def test_query_count_git(self):
        if not self.supports_git:
            self.skipTest("Context doesn't support Git repositories.")
        with admin_logged_in():
            for i in range(7):
                self.makeGitMergeProposal()
        flush_database_caches()
        with StormStatementRecorder() as recorder:
            self.getViewBrowser(
                self.context, self.view_name, rootsite='code', user=self.user)
        self.assertThat(recorder, HasQueryCount(LessThan(47)))


class MergesTestMixin(BranchMergeProposalListingTestMixin):

    view_name = '+merges'
    page_title = 'Merge proposals'

    def test_none(self):
        """The merges view should be enabled for the target."""
        browser = self.getViewBrowser(
            self.context, self.view_name, rootsite='code', user=self.user)
        self.assertIn("has no merge proposals", browser.contents)


class DependentMergesTestMixin(BranchMergeProposalListingTestMixin):

    view_name = '+dependent-merges'
    page_title = 'Dependent merge proposals'

    def makeBzrMergeProposal(self):
        information_type = (
            InformationType.USERDATA if self.supports_privacy else None)
        prerequisite = self.bzr_branch
        if prerequisite is None:
            prerequisite = self.factory.makeBranch(
                target=self.bzr_target, information_type=information_type)
        target = self.factory.makeBranch(
            target=self.bzr_target, information_type=information_type)
        source = self.factory.makeBranch(
            target=self.bzr_target, owner=self.owner,
            information_type=information_type)
        return self.factory.makeBranchMergeProposal(
            source_branch=source, target_branch=target,
            prerequisite_branch=prerequisite,
            set_state=BranchMergeProposalStatus.NEEDS_REVIEW)

    def makeGitMergeProposal(self):
        information_type = (
            InformationType.USERDATA if self.supports_privacy else None)
        prerequisite = self.git_ref
        if prerequisite is None:
            [prerequisite] = self.factory.makeGitRefs(
                target=self.git_target, information_type=information_type)
        [target] = self.factory.makeGitRefs(
            target=self.git_target, information_type=information_type)
        [source] = self.factory.makeGitRefs(
            target=self.git_target, owner=self.owner,
            information_type=information_type)
        return self.factory.makeBranchMergeProposalForGit(
            source_ref=source, target_ref=target,
            prerequisite_ref=prerequisite,
            set_state=BranchMergeProposalStatus.NEEDS_REVIEW)

    def getExpectedLabel(self):
        return "Merge proposals dependent on %s" % self.context.displayname

    def test_none(self):
        """The dependent merges view should be enabled for the target."""
        browser = self.getViewBrowser(
            self.context, self.view_name, rootsite='code', user=self.user)
        self.assertIn("has no merge proposals", browser.contents)


class ActiveReviewsTestMixin(BranchMergeProposalListingTestMixin):

    view_name = '+activereviews'
    page_title = 'Active reviews'

    def test_none(self):
        """The active reviews view should be enabled for the target."""
        browser = self.getViewBrowser(
            self.context, self.view_name, rootsite='code', user=self.user)
        self.assertIn("has no active code reviews", browser.contents)


class ProductContextMixin:

    label_describes_context = False

    def setUp(self):
        super(ProductContextMixin, self).setUp()
        self.git_target = self.bzr_target = self.context = (
            self.factory.makeProduct())
        self.user = self.git_target.owner
        self.owner = None


class ProjectGroupContextMixin:

    label_describes_context = False

    def setUp(self):
        super(ProjectGroupContextMixin, self).setUp()
        self.context = self.factory.makeProject()
        self.git_target = self.bzr_target = self.factory.makeProduct(
            projectgroup=self.context)
        self.user = self.git_target.owner
        self.owner = None


class DistributionSourcePackageContextMixin:

    # Distribution branches don't have access_policy set.
    supports_privacy = False
    label_describes_context = False

    def setUp(self):
        super(DistributionSourcePackageContextMixin, self).setUp()
        self.git_target = self.context = (
            self.factory.makeDistributionSourcePackage())
        with admin_logged_in():
            getUtility(IService, "sharing").sharePillarInformation(
                self.context.distribution, self.context.distribution.owner,
                self.context.distribution.owner,
                {InformationType.USERDATA: SharingPermission.ALL})
        distroseries = self.factory.makeDistroSeries(
            distribution=self.context.distribution)
        self.bzr_target = distroseries.getSourcePackage(
            self.context.sourcepackagename)
        self.user = self.context.distribution.owner
        self.owner = None


class SourcePackageContextMixin:

    # Distribution branches don't have access_policy set.
    supports_privacy = False
    supports_git = False

    def setUp(self):
        super(SourcePackageContextMixin, self).setUp()
        self.bzr_target = self.context = self.factory.makeSourcePackage()
        self.user = self.context.distribution.owner
        self.owner = None


class PersonContextMixin:

    label_describes_context = False

    def setUp(self):
        super(PersonContextMixin, self).setUp()
        self.context = self.factory.makePerson()
        self.bzr_target = self.git_target = self.factory.makeProduct()
        self.user = self.bzr_target.owner
        self.owner = self.context


class PersonProductContextMixin:

    label_describes_context = False

    def setUp(self):
        super(PersonProductContextMixin, self).setUp()
        self.context = PersonProduct(
            self.factory.makePerson(), self.factory.makeProduct())
        self.bzr_target = self.git_target = self.context.product
        self.user = self.context.product.owner
        self.owner = self.context.person


class BranchContextMixin:

    supports_git = False

    def setUp(self):
        super(BranchContextMixin, self).setUp()
        self.bzr_target = self.factory.makeProduct()
        self.context = self.bzr_branch = self.factory.makeBranch(
            target=self.bzr_target)
        self.user = self.bzr_target.owner
        self.owner = None


class GitRefContextMixin:

    supports_bzr = False

    def setUp(self):
        super(GitRefContextMixin, self).setUp()
        self.git_target = self.factory.makeProduct()
        self.context = self.git_ref = self.factory.makeGitRefs(
            target=self.git_target)[0]
        self.user = self.git_target.owner
        self.owner = None


class TestProductMerges(
        ProductContextMixin, MergesTestMixin, BrowserTestCase):

    pass


class TestProjectGroupMerges(
        ProjectGroupContextMixin, MergesTestMixin, BrowserTestCase):

    pass


class TestDistributionSourcePackageMerges(
        DistributionSourcePackageContextMixin, MergesTestMixin,
        BrowserTestCase):

    pass


class TestSourcePackageMerges(
        SourcePackageContextMixin, MergesTestMixin, BrowserTestCase):

    pass


class TestPersonMerges(PersonContextMixin, MergesTestMixin, BrowserTestCase):

    pass


class TestPersonProductMerges(
        PersonProductContextMixin, MergesTestMixin, BrowserTestCase):

    pass


class TestBranchMerges(BranchContextMixin, MergesTestMixin, BrowserTestCase):

    pass


class TestGitRefMerges(GitRefContextMixin, MergesTestMixin, BrowserTestCase):

    pass


class TestBranchDependentMerges(
        BranchContextMixin, DependentMergesTestMixin, BrowserTestCase):

    pass


class TestGitRefDependentMerges(
        GitRefContextMixin, DependentMergesTestMixin, BrowserTestCase):

    pass


class TestProductActiveReviews(
        ProductContextMixin, ActiveReviewsTestMixin, BrowserTestCase):

    pass


class TestProjectGroupActiveReviews(
        ProjectGroupContextMixin, ActiveReviewsTestMixin, BrowserTestCase):

    pass


class TestDistributionSourcePackageActiveReviews(
        DistributionSourcePackageContextMixin, ActiveReviewsTestMixin,
        BrowserTestCase):

    pass


class TestSourcePackageActiveReviews(
        SourcePackageContextMixin, ActiveReviewsTestMixin, BrowserTestCase):

    pass


class TestPersonActiveReviews(
        PersonContextMixin, ActiveReviewsTestMixin, BrowserTestCase):

    pass


class TestPersonProductActiveReviews(
        PersonProductContextMixin, ActiveReviewsTestMixin, BrowserTestCase):

    pass


class TestBranchActiveReviews(
        BranchContextMixin, ActiveReviewsTestMixin, BrowserTestCase):

    pass


class TestGitRefActiveReviews(
        GitRefContextMixin, ActiveReviewsTestMixin, BrowserTestCase):

    pass


class ActiveReviewGroupsTestMixin:
    """Tests for groupings used for active reviews."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(ActiveReviewGroupsTestMixin, self).setUp()
        self.bmp = self._makeBranchMergeProposal(
            set_state=BranchMergeProposalStatus.NEEDS_REVIEW)

    def assertReviewGroupForReviewer(self, reviewer, group):
        # Assert that the group for the reviewer is correct.
        login(ANONYMOUS)
        # The actual context of the view doesn't matter here as all the
        # parameters are passed in.
        view = create_initialized_view(
            self.factory.makeProduct(), '+activereviews', rootsite='code')
        self.assertEqual(
            group, view._getReviewGroup(self.bmp, self.bmp.votes, reviewer))

    def test_unrelated_reviewer(self):
        # If the reviewer is not otherwise related to the proposal, the group
        # is other.
        reviewer = self.factory.makePerson()
        self.assertReviewGroupForReviewer(reviewer, ActiveReviewsView.OTHER)

    def test_approved(self):
        # If the proposal is approved, then the group is approved.
        self.bmp = self._makeBranchMergeProposal(
            set_state=BranchMergeProposalStatus.CODE_APPROVED)
        self.assertReviewGroupForReviewer(None, ActiveReviewsView.APPROVED)

    def test_work_in_progress(self):
        # If the proposal is in progress, then the group is wip.
        self.bmp = self._makeBranchMergeProposal(
            set_state=BranchMergeProposalStatus.WORK_IN_PROGRESS)
        self.assertReviewGroupForReviewer(None, ActiveReviewsView.WIP)

    def test_merge_source_owner(self):
        # If the reviewer is the owner of the merge source, then the review
        # is MINE.  This occurs whether or not the user is the logged in or
        # not.
        reviewer = self.bmp.merge_source.owner
        self.assertReviewGroupForReviewer(reviewer, ActiveReviewsView.MINE)

    def test_proposal_registrant(self):
        # If the reviewer is the registrant of the proposal, then it is MINE
        # only if the registrant is a member of the team that owns the branch.
        reviewer = self.bmp.registrant
        self.assertReviewGroupForReviewer(reviewer, ActiveReviewsView.OTHER)

        team = self.factory.makeTeam(self.bmp.registrant)
        naked_merge_source = removeSecurityProxy(self.bmp.merge_source)
        if IGitRef.providedBy(naked_merge_source):
            naked_merge_source.repository.owner = team
        else:
            naked_merge_source.owner = team
        self.assertReviewGroupForReviewer(reviewer, ActiveReviewsView.MINE)

    def test_merge_target_owner(self):
        # For the merge target owner, it is to_do since they are the default
        # reviewer.
        reviewer = self.bmp.merge_target.owner
        self.assertReviewGroupForReviewer(reviewer, ActiveReviewsView.TO_DO)

    def test_group_pending_review(self):
        # If the reviewer in user has a pending review request, it is a TO_DO.
        reviewer = self.factory.makePerson()
        login_person(self.bmp.registrant)
        self.bmp.nominateReviewer(reviewer, self.bmp.registrant)
        self.assertReviewGroupForReviewer(reviewer, ActiveReviewsView.TO_DO)

    def test_group_pending_team_review(self):
        # If the logged in user of a team that has a pending review request,
        # it is a CAN_DO.
        reviewer = self.factory.makePerson()
        login_person(self.bmp.registrant)
        team = self.factory.makeTeam(reviewer)
        self.bmp.nominateReviewer(team, self.bmp.registrant)
        self.assertReviewGroupForReviewer(reviewer, ActiveReviewsView.CAN_DO)

    def test_review_done(self):
        # If the logged in user has a completed review, then the review is
        # ARE_DOING.
        reviewer = self.bmp.merge_target.owner
        login_person(reviewer)
        self.bmp.createComment(
            reviewer, 'subject', vote=CodeReviewVote.APPROVE)
        self.assertReviewGroupForReviewer(
            reviewer, ActiveReviewsView.ARE_DOING)


class ActiveReviewGroupsTestBzr(
    ActiveReviewGroupsTestMixin, BzrMixin, TestCaseWithFactory):
    """Tests for groupings used for active reviews for Bazaar."""


class ActiveReviewGroupsTestGit(
    ActiveReviewGroupsTestMixin, GitMixin, TestCaseWithFactory):
    """Tests for groupings used for active reviews for Git."""


class TestBranchMergeProposalListingItemMixin:
    """Tests specifically relating to the BranchMergeProposalListingItem."""

    layer = DatabaseFunctionalLayer

    def test_sort_key_needs_review(self):
        # If the proposal is in needs review, the sort_key will be the
        # date_review_requested.
        bmp = self.factory.makeBranchMergeProposal(
            date_created=datetime(2009, 6, 1, tzinfo=pytz.UTC))
        login_person(bmp.registrant)
        request_date = datetime(2009, 7, 1, tzinfo=pytz.UTC)
        bmp.requestReview(request_date)
        item = BranchMergeProposalListingItem(bmp, None, None)
        self.assertEqual(request_date, item.sort_key)

    def test_sort_key_approved(self):
        # If the proposal is approved, the sort_key will default to the
        # date_review_requested.
        bmp = self.factory.makeBranchMergeProposal(
            date_created=datetime(2009, 6, 1, tzinfo=pytz.UTC))
        login_person(bmp.target_branch.owner)
        request_date = datetime(2009, 7, 1, tzinfo=pytz.UTC)
        bmp.requestReview(request_date)
        bmp.approveBranch(
            bmp.target_branch.owner, 'rev-id',
            datetime(2009, 8, 1, tzinfo=pytz.UTC))
        item = BranchMergeProposalListingItem(bmp, None, None)
        self.assertEqual(request_date, item.sort_key)

    def test_sort_key_approved_from_wip(self):
        # If the proposal is approved and the review has been bypassed, the
        # date_reviewed is used.
        bmp = self.factory.makeBranchMergeProposal(
            date_created=datetime(2009, 6, 1, tzinfo=pytz.UTC))
        login_person(bmp.target_branch.owner)
        review_date = datetime(2009, 8, 1, tzinfo=pytz.UTC)
        bmp.approveBranch(
            bmp.target_branch.owner, 'rev-id', review_date)
        item = BranchMergeProposalListingItem(bmp, None, None)
        self.assertEqual(review_date, item.sort_key)

    def test_sort_key_wip(self):
        # If the proposal is a work in progress, the date_created is used.
        bmp = self.factory.makeBranchMergeProposal(
            date_created=datetime(2009, 6, 1, tzinfo=pytz.UTC))
        login_person(bmp.target_branch.owner)
        item = BranchMergeProposalListingItem(bmp, None, None)
        self.assertEqual(bmp.date_created, item.sort_key)


class TestBranchMergeProposalListingItemBzr(
    TestBranchMergeProposalListingItemMixin, BzrMixin, TestCaseWithFactory):
    """Test BranchMergeProposalListingItem for Bazaar."""


class TestBranchMergeProposalListingItemGit(
    TestBranchMergeProposalListingItemMixin, GitMixin, TestCaseWithFactory):
    """Test BranchMergeProposalListingItem for Git."""


class ActiveReviewSortingTestMixin:
    """Test the sorting of the active review groups."""

    layer = DatabaseFunctionalLayer

    def test_oldest_first(self):
        # The oldest requested reviews should be first.
        product = self.factory.makeProduct()
        bmp1 = self._makeBranchMergeProposal(target=product)
        login_person(bmp1.merge_source.owner)
        bmp1.requestReview(datetime(2009, 6, 1, tzinfo=pytz.UTC))
        bmp2 = self._makeBranchMergeProposal(target=product)
        login_person(bmp2.merge_source.owner)
        bmp2.requestReview(datetime(2009, 3, 1, tzinfo=pytz.UTC))
        bmp3 = self._makeBranchMergeProposal(target=product)
        login_person(bmp3.merge_source.owner)
        bmp3.requestReview(datetime(2009, 1, 1, tzinfo=pytz.UTC))
        login(ANONYMOUS)
        view = create_initialized_view(
            product, name='+activereviews', rootsite='code')
        self.assertEqual(
            [bmp3, bmp2, bmp1],
            [item.context for item in view.review_groups[view.OTHER]])


class ActiveReviewSortingTestBzr(
    ActiveReviewSortingTestMixin, BzrMixin, TestCaseWithFactory):
    """Test the sorting of the active review groups for Bazaar."""


class ActiveReviewSortingTestGit(
    ActiveReviewSortingTestMixin, GitMixin, TestCaseWithFactory):
    """Test the sorting of the active review groups for Git."""


class ActiveReviewsOfBranchesMixin:
    """Test reviews of branches."""

    layer = DatabaseFunctionalLayer

    def test_no_proposal_message(self):
        branch = self._makeBranch()
        view = create_initialized_view(
            branch, name='+activereviews', rootsite='code')
        self.assertEqual(
            "%s has no active code reviews." % branch.display_name,
            view.no_proposal_message)

    def test_private_branch_owner(self):
        # Merge proposals against private branches are visible to
        # the branch owner.
        product = self.factory.makeProduct()
        branch = self._makeBranch(
            target=product, information_type=InformationType.USERDATA)
        with person_logged_in(removeSecurityProxy(branch).owner):
            mp = self._makeBranchMergeProposal(merge_target=branch)
            view = create_initialized_view(
                branch, name='+activereviews', rootsite='code')
            self.assertEqual([mp], list(view.getProposals()))


class ActiveReviewsOfBranchesBzr(
    ActiveReviewsOfBranchesMixin, BzrMixin, TestCaseWithFactory):
    """Test reviews of Bazaar branches."""


class ActiveReviewsOfBranchesGit(
    ActiveReviewsOfBranchesMixin, GitMixin, TestCaseWithFactory):
    """Test reviews of references in Git repositories."""


class ActiveReviewsPerformanceMixin:
    """Test the performance of the active reviews page."""

    layer = LaunchpadFunctionalLayer

    def setupBMP(self, bmp):
        self.factory.makePreviewDiff(merge_proposal=bmp)
        login_person(bmp.merge_source.owner)
        bmp.requestReview()

    def createUserBMP(self, reviewer=None, merge_target_owner=None):
        merge_target = None
        if merge_target_owner is not None:
            merge_target = self._makePackageBranch(
                owner=merge_target_owner)
        bmp = self._makeBranchMergeProposal(
            reviewer=reviewer, merge_target=merge_target)
        self.setupBMP(bmp)
        return bmp

    def createUserBMPsAndRecordQueries(self, number_of_bmps):
        # Create {number_of_bmps} branch merge proposals related to a
        # user, render the person's +activereviews page, and return the
        # view and a recorder of the queries generated by this page
        # rendering.
        user = self.factory.makePerson()
        for i in xrange(number_of_bmps):
            # Create one of the two types of BMP which will be displayed
            # on a person's +activereviews page:
            # - A BMP for which the person is the reviewer.
            # - A BMP for which the person is the owner of the merge target.
            if i % 2 == 0:
                self.createUserBMP(merge_target_owner=user)
            else:
                self.createUserBMP(reviewer=user)
        login_person(user)
        flush_database_caches()
        with StormStatementRecorder() as recorder:
            view = create_initialized_view(
                user, name='+activereviews', rootsite='code', principal=user)
            view.render()
        return recorder, view

    def test_person_activereviews_query_count(self):
        base_bmps = 3
        added_bmps = 4
        recorder1, view1 = self.createUserBMPsAndRecordQueries(base_bmps)
        self.assertEqual(base_bmps, view1.proposal_count)
        self.addDetail("r1tb", Content(UTF8_TEXT, lambda: [str(recorder1)]))
        recorder2, view2 = self.createUserBMPsAndRecordQueries(
            base_bmps + added_bmps)
        self.assertEqual(base_bmps + added_bmps, view2.proposal_count)
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))

    def createProductBMP(self, product):
        merge_target = self._makeStackedOnBranchChain(target=product)
        bmp = self._makeBranchMergeProposal(
            target=product, merge_target=merge_target)
        self.setupBMP(bmp)
        return bmp

    def createProductBMPsAndRecordQueries(self, number_of_bmps):
        # Create {number_of_bmps} branch merge proposals related to a
        # product, render the product's +activereviews page, and return the
        # view and a recorder of the queries generated by this page
        # rendering.
        product = self.factory.makeProduct()
        for i in xrange(number_of_bmps):
            self.createProductBMP(product=product)
        login_person(product.owner)
        flush_database_caches()
        with StormStatementRecorder() as recorder:
            view = create_initialized_view(
                product, name='+activereviews', rootsite='code',
                principal=product.owner)
            view.render()
        return recorder, view

    def test_product_activereviews_query_count(self):
        # We keep the number of bmps created small (3 and 7), see above.
        base_bmps = 3
        added_bmps = 4
        recorder1, view1 = self.createProductBMPsAndRecordQueries(base_bmps)
        self.assertEqual(base_bmps, view1.proposal_count)
        self.addDetail("r1tb", Content(UTF8_TEXT, lambda: [str(recorder1)]))
        recorder2, view2 = self.createProductBMPsAndRecordQueries(
            base_bmps + added_bmps)
        self.assertEqual(base_bmps + added_bmps, view2.proposal_count)
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))


class ActiveReviewsPerformanceBzr(
    ActiveReviewsPerformanceMixin, BzrMixin, TestCaseWithFactory):
    """Test the performance of the active reviews page for Bazaar."""


class ActiveReviewsPerformanceGit(
    ActiveReviewsPerformanceMixin, GitMixin, TestCaseWithFactory):
    """Test the performance of the active reviews page for Git."""
