# Copyright 2015-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Git references."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )
import hashlib
import json

import pytz
from testtools.matchers import (
    ContainsDict,
    EndsWith,
    Equals,
    Is,
    LessThan,
    MatchesListwise,
    MatchesStructure,
    )
from zope.component import getUtility

from lp.app.enums import InformationType
from lp.app.interfaces.informationtype import IInformationType
from lp.app.interfaces.launchpad import IPrivacy
from lp.code.errors import InvalidBranchMergeProposal
from lp.code.tests.helpers import GitHostingFixture
from lp.services.features.testing import FeatureFixture
from lp.services.memcache.interfaces import IMemcacheClient
from lp.services.webapp.interfaces import OAuthPermission
from lp.testing import (
    admin_logged_in,
    ANONYMOUS,
    api_url,
    person_logged_in,
    record_two_runs,
    TestCaseWithFactory,
    verifyObject,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing.matchers import HasQueryCount
from lp.testing.pages import webservice_for_person


class TestGitRef(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_display_name(self):
        [master, personal] = self.factory.makeGitRefs(
            paths=["refs/heads/master", "refs/heads/people/foo/bar"])
        repo_path = master.repository.shortened_path
        self.assertEqual(
            ["%s:master" % repo_path, "%s:people/foo/bar" % repo_path],
            [ref.display_name for ref in (master, personal)])

    def test_getMergeProposals(self):
        [target_ref] = self.factory.makeGitRefs()
        bmp = self.factory.makeBranchMergeProposalForGit(target_ref=target_ref)
        self.factory.makeBranchMergeProposalForGit()
        self.assertEqual([bmp], list(target_ref.getMergeProposals()))

    def test_getDependentMergeProposals(self):
        [prerequisite_ref] = self.factory.makeGitRefs()
        bmp = self.factory.makeBranchMergeProposalForGit(
            prerequisite_ref=prerequisite_ref)
        self.factory.makeBranchMergeProposalForGit()
        self.assertEqual(
            [bmp], list(prerequisite_ref.getDependentMergeProposals()))

    def test_implements_IInformationType(self):
        [ref] = self.factory.makeGitRefs()
        verifyObject(IInformationType, ref)

    def test_implements_IPrivacy(self):
        [ref] = self.factory.makeGitRefs()
        verifyObject(IPrivacy, ref)

    def test_refs_in_private_repositories_are_private(self):
        [ref] = self.factory.makeGitRefs(
            information_type=InformationType.USERDATA)
        self.assertTrue(ref.private)
        self.assertEqual(InformationType.USERDATA, ref.information_type)


class TestGitRefGetCommits(TestCaseWithFactory):
    """Tests for retrieving commit information from a Git reference."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestGitRefGetCommits, self).setUp()
        [self.ref] = self.factory.makeGitRefs()
        self.authors = [self.factory.makePerson() for _ in range(2)]
        with admin_logged_in():
            self.author_emails = [
                author.preferredemail.email for author in self.authors]
        epoch = datetime.fromtimestamp(0, tz=pytz.UTC)
        self.dates = [
            datetime(2015, 1, 1, 0, 0, 0, tzinfo=pytz.UTC),
            datetime(2015, 1, 2, 0, 0, 0, tzinfo=pytz.UTC),
            ]
        self.sha1_tip = unicode(hashlib.sha1("tip").hexdigest())
        self.sha1_root = unicode(hashlib.sha1("root").hexdigest())
        self.log = [
            {
                "sha1": self.sha1_tip,
                "message": "tip",
                "author": {
                    "name": self.authors[0].display_name,
                    "email": self.author_emails[0],
                    "time": int((self.dates[1] - epoch).total_seconds()),
                    },
                "committer": {
                    "name": self.authors[1].display_name,
                    "email": self.author_emails[1],
                    "time": int((self.dates[1] - epoch).total_seconds()),
                    },
                "parents": [self.sha1_root],
                "tree": unicode(hashlib.sha1("").hexdigest()),
                },
            {
                "sha1": self.sha1_root,
                "message": "root",
                "author": {
                    "name": self.authors[1].display_name,
                    "email": self.author_emails[1],
                    "time": int((self.dates[0] - epoch).total_seconds()),
                    },
                "committer": {
                    "name": self.authors[0].display_name,
                    "email": self.author_emails[0],
                    "time": int((self.dates[0] - epoch).total_seconds()),
                    },
                "parents": [],
                "tree": unicode(hashlib.sha1("").hexdigest()),
                },
            ]
        self.hosting_fixture = self.useFixture(GitHostingFixture(log=self.log))

    def test_basic(self):
        commits = self.ref.getCommits(self.sha1_tip)
        path = self.ref.repository.getInternalPath()
        self.assertEqual(
            [((path, self.sha1_tip),
              {"limit": None, "stop": None, "logger": None})],
            self.hosting_fixture.getLog.calls)
        self.assertThat(commits, MatchesListwise([
            ContainsDict({
                "sha1": Equals(self.sha1_tip),
                "author": MatchesStructure.byEquality(person=self.authors[0]),
                "author_date": Equals(self.dates[1]),
                "commit_message": Equals("tip"),
                }),
            ContainsDict({
                "sha1": Equals(self.sha1_root),
                "author": MatchesStructure.byEquality(person=self.authors[1]),
                "author_date": Equals(self.dates[0]),
                "commit_message": Equals("root"),
                }),
            ]))
        key = "git.launchpad.dev:git-log:%s:%s" % (path, self.sha1_tip)
        self.assertEqual(
            json.dumps(self.log),
            getUtility(IMemcacheClient).get(key.encode("UTF-8")))

    def test_cache(self):
        path = self.ref.repository.getInternalPath()
        key = "git.launchpad.dev:git-log:%s:%s" % (path, self.sha1_tip)
        getUtility(IMemcacheClient).set(key.encode("UTF-8"), "[]")
        self.assertEqual([], self.ref.getCommits(self.sha1_tip))

    def test_disable_hosting(self):
        self.useFixture(
            FeatureFixture({"code.git.log.disable_hosting": "on"}))
        commits = self.ref.getCommits(self.sha1_tip)
        self.assertThat(commits, MatchesListwise([
            ContainsDict({
                "sha1": Equals(self.ref.commit_sha1),
                "commit_message": Is(None),
                }),
            ]))
        self.assertEqual([], self.hosting_fixture.getLog.calls)
        path = self.ref.repository.getInternalPath()
        key = "git.launchpad.dev:git-log:%s:%s" % (path, self.sha1_tip)
        self.assertIsNone(getUtility(IMemcacheClient).get(key.encode("UTF-8")))

    def test_disable_memcache(self):
        self.useFixture(
            FeatureFixture({"code.git.log.disable_memcache": "on"}))
        path = self.ref.repository.getInternalPath()
        key = "git.launchpad.dev:git-log:%s:%s" % (path, self.sha1_tip)
        getUtility(IMemcacheClient).set(key.encode("UTF-8"), "[]")
        self.assertNotEqual([], self.ref.getCommits(self.sha1_tip))
        self.assertEqual(
            "[]", getUtility(IMemcacheClient).get(key.encode("UTF-8")))

    def test_limit_stop(self):
        self.ref.getCommits(self.sha1_tip, limit=10, stop=self.sha1_root)
        path = self.ref.repository.getInternalPath()
        self.assertEqual(
            [((path, self.sha1_tip),
              {"limit": 10, "stop": self.sha1_root, "logger": None})],
            self.hosting_fixture.getLog.calls)
        key = "git.launchpad.dev:git-log:%s:%s:limit=10:stop=%s" % (
            path, self.sha1_tip, self.sha1_root)
        self.assertEqual(
            json.dumps(self.log),
            getUtility(IMemcacheClient).get(key.encode("UTF-8")))

    def test_union_repository(self):
        other_repository = self.factory.makeGitRepository()
        self.ref.getCommits(
            self.sha1_tip, stop=self.sha1_root,
            union_repository=other_repository)
        path = "%s:%s" % (
            other_repository.getInternalPath(),
            self.ref.repository.getInternalPath())
        self.assertEqual(
            [((path, self.sha1_tip),
              {"limit": None, "stop": self.sha1_root, "logger": None})],
            self.hosting_fixture.getLog.calls)
        key = "git.launchpad.dev:git-log:%s:%s:stop=%s" % (
            path, self.sha1_tip, self.sha1_root)
        self.assertEqual(
            json.dumps(self.log),
            getUtility(IMemcacheClient).get(key.encode("UTF-8")))

    def test_start_date(self):
        commits = self.ref.getCommits(
            self.sha1_tip, start_date=(self.dates[1] - timedelta(seconds=1)))
        path = self.ref.repository.getInternalPath()
        self.assertThat(commits, MatchesListwise([
            ContainsDict({"sha1": Equals(self.sha1_tip)}),
            ]))
        key = "git.launchpad.dev:git-log:%s:%s" % (path, self.sha1_tip)
        self.assertEqual(
            json.dumps(self.log),
            getUtility(IMemcacheClient).get(key.encode("UTF-8")))

    def test_end_date(self):
        commits = self.ref.getCommits(
            self.sha1_tip, end_date=(self.dates[1] - timedelta(seconds=1)))
        self.assertThat(commits, MatchesListwise([
            ContainsDict({"sha1": Equals(self.sha1_root)}),
            ]))

    def test_extended_details_with_merge(self):
        mp = self.factory.makeBranchMergeProposalForGit(target_ref=self.ref)
        mp.markAsMerged(merged_revision_id=self.sha1_tip)
        revisions = self.ref.getLatestCommits(
            self.sha1_tip, extended_details=True, user=self.ref.owner)
        self.assertThat(revisions, MatchesListwise([
            ContainsDict({
                "sha1": Equals(self.sha1_tip),
                "merge_proposal": Equals(mp),
                }),
            ContainsDict({
                "sha1": Equals(self.sha1_root),
                "merge_proposal": Is(None),
                }),
            ]))


class TestGitRefCreateMergeProposal(TestCaseWithFactory):
    """Exercise all the code paths for creating a merge proposal."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestGitRefCreateMergeProposal, self).setUp()
        with admin_logged_in():
            self.project = self.factory.makeProduct()
            self.user = self.factory.makePerson()
            self.reviewer = self.factory.makePerson(name="reviewer")
            [self.source] = self.factory.makeGitRefs(
                name="source", owner=self.user, target=self.project)
            [self.target] = self.factory.makeGitRefs(
                name="target", owner=self.user, target=self.project)
            [self.prerequisite] = self.factory.makeGitRefs(
                name="prerequisite", owner=self.user, target=self.project)

    def assertOnePendingReview(self, proposal, reviewer, review_type=None):
        # There should be one pending vote for the reviewer with the specified
        # review type.
        [vote] = proposal.votes
        self.assertEqual(reviewer, vote.reviewer)
        self.assertEqual(self.user, vote.registrant)
        self.assertIsNone(vote.comment)
        if review_type is None:
            self.assertIsNone(vote.review_type)
        else:
            self.assertEqual(review_type, vote.review_type)

    def test_personal_source(self):
        """Personal repositories cannot be used as a source for MPs."""
        self.source.repository.setTarget(
            target=self.source.owner, user=self.source.owner)
        self.assertRaises(
            InvalidBranchMergeProposal, self.source.addLandingTarget,
            self.user, self.target)

    def test_target_repository_same_target(self):
        """The target repository's target must match that of the source."""
        self.target.repository.setTarget(
            target=self.target.owner, user=self.target.owner)
        self.assertRaises(
            InvalidBranchMergeProposal, self.source.addLandingTarget,
            self.user, self.target)

        project = self.factory.makeProduct()
        self.target.repository.setTarget(
            target=project, user=self.target.owner)
        self.assertRaises(
            InvalidBranchMergeProposal, self.source.addLandingTarget,
            self.user, self.target)

    def test_target_must_not_be_the_source(self):
        """The target and source references cannot be the same."""
        self.assertRaises(
            InvalidBranchMergeProposal, self.source.addLandingTarget,
            self.user, self.source)

    def test_prerequisite_repository_same_target(self):
        """The prerequisite repository, if any, must be for the same target."""
        self.prerequisite.repository.setTarget(
            target=self.prerequisite.owner, user=self.prerequisite.owner)
        self.assertRaises(
            InvalidBranchMergeProposal, self.source.addLandingTarget,
            self.user, self.target, self.prerequisite)

        project = self.factory.makeProduct()
        self.prerequisite.repository.setTarget(
            target=project, user=self.prerequisite.owner)
        self.assertRaises(
            InvalidBranchMergeProposal, self.source.addLandingTarget,
            self.user, self.target, self.prerequisite)

    def test_prerequisite_must_not_be_the_source(self):
        """The target and source references cannot be the same."""
        self.assertRaises(
            InvalidBranchMergeProposal, self.source.addLandingTarget,
            self.user, self.target, self.source)

    def test_prerequisite_must_not_be_the_target(self):
        """The target and source references cannot be the same."""
        self.assertRaises(
            InvalidBranchMergeProposal, self.source.addLandingTarget,
            self.user, self.target, self.target)

    def test_existingMergeProposal(self):
        """If there is an existing merge proposal for the source and target
        reference pair, then another landing target specifying the same pair
        raises.
        """
        self.source.addLandingTarget(self.user, self.target, self.prerequisite)
        self.assertRaises(
            InvalidBranchMergeProposal, self.source.addLandingTarget,
            self.user, self.target, self.prerequisite)

    def test_existingRejectedMergeProposal(self):
        """If there is an existing rejected merge proposal for the source
        and target reference pair, then another landing target specifying
        the same pair is fine.
        """
        proposal = self.source.addLandingTarget(
            self.user, self.target, self.prerequisite)
        proposal.rejectBranch(self.user, "some_revision")
        self.source.addLandingTarget(self.user, self.target, self.prerequisite)

    def test_default_reviewer(self):
        """If the target repository has a default reviewer set, this
        reviewer should be assigned to the merge proposal.
        """
        [target_with_default_reviewer] = self.factory.makeGitRefs(
            name="target-branch-with-reviewer", owner=self.user,
            target=self.project, reviewer=self.reviewer)
        proposal = self.source.addLandingTarget(
            self.user, target_with_default_reviewer)
        self.assertOnePendingReview(proposal, self.reviewer)

    def test_default_reviewer_when_owner(self):
        """If the target repository has a no default reviewer set, the
        repository owner should be assigned as the reviewer for the merge
        proposal.
        """
        proposal = self.source.addLandingTarget(self.user, self.target)
        self.assertOnePendingReview(proposal, self.source.owner)

    def test_attribute_assignment(self):
        """Smoke test to make sure the assignments are there."""
        commit_message = "Some commit message"
        proposal = self.source.addLandingTarget(
            self.user, self.target, self.prerequisite,
            commit_message=commit_message)
        self.assertEqual(self.user, proposal.registrant)
        self.assertEqual(self.source, proposal.merge_source)
        self.assertEqual(self.target, proposal.merge_target)
        self.assertEqual(self.prerequisite, proposal.merge_prerequisite)
        self.assertEqual(commit_message, proposal.commit_message)

    def test_createMergeProposal_with_reviewers(self):
        person1 = self.factory.makePerson()
        person2 = self.factory.makePerson()
        e = self.assertRaises(
            ValueError, self.source.createMergeProposal,
            self.user, self.target, reviewers=[person1, person2])
        self.assertEqual(
            "reviewers and review_types must be equal length.", str(e))
        e = self.assertRaises(
            ValueError, self.source.createMergeProposal,
            self.user, self.target, reviewers=[person1, person2],
            review_types=["review1"])
        self.assertEqual(
            "reviewers and review_types must be equal length.", str(e))
        bmp = self.source.createMergeProposal(
            self.user, self.target, reviewers=[person1, person2],
            review_types=["review1", "review2"])
        votes = {(vote.reviewer, vote.review_type) for vote in bmp.votes}
        self.assertEqual({(person1, "review1"), (person2, "review2")}, votes)


class TestGitRefWebservice(TestCaseWithFactory):
    """Tests for the webservice."""

    layer = DatabaseFunctionalLayer

    def test_attributes(self):
        [master] = self.factory.makeGitRefs(paths=["refs/heads/master"])
        webservice = webservice_for_person(
            master.repository.owner, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        with person_logged_in(ANONYMOUS):
            repository_url = api_url(master.repository)
            master_url = api_url(master)
        response = webservice.get(master_url)
        self.assertEqual(200, response.status)
        result = response.jsonBody()
        self.assertThat(result["repository_link"], EndsWith(repository_url))
        self.assertEqual("refs/heads/master", result["path"])
        self.assertEqual(
            unicode(hashlib.sha1("refs/heads/master").hexdigest()),
            result["commit_sha1"])

    def test_landing_candidates(self):
        bmp_db = self.factory.makeBranchMergeProposalForGit()
        with person_logged_in(bmp_db.registrant):
            bmp_url = api_url(bmp_db)
            ref_url = api_url(bmp_db.target_git_ref)
        webservice = webservice_for_person(
            bmp_db.registrant, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        ref = webservice.get(ref_url).jsonBody()
        landing_candidates = webservice.get(
            ref["landing_candidates_collection_link"]).jsonBody()
        self.assertEqual(1, len(landing_candidates["entries"]))
        self.assertThat(
            landing_candidates["entries"][0]["self_link"], EndsWith(bmp_url))

    def test_landing_candidates_constant_queries(self):
        project = self.factory.makeProduct()
        with person_logged_in(project.owner):
            [trunk] = self.factory.makeGitRefs(target=project)
            trunk_url = api_url(trunk)
            webservice = webservice_for_person(
                project.owner, permission=OAuthPermission.WRITE_PRIVATE)

        def create_mp():
            with admin_logged_in():
                [ref] = self.factory.makeGitRefs(
                    target=project,
                    information_type=InformationType.PRIVATESECURITY)
                self.factory.makeBranchMergeProposalForGit(
                    source_ref=ref, target_ref=trunk)

        def list_mps():
            webservice.get(trunk_url + "/landing_candidates")

        list_mps()
        recorder1, recorder2 = record_two_runs(list_mps, create_mp, 2)
        self.assertThat(recorder1, HasQueryCount(LessThan(30)))
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))

    def test_landing_targets(self):
        bmp_db = self.factory.makeBranchMergeProposalForGit()
        with person_logged_in(bmp_db.registrant):
            bmp_url = api_url(bmp_db)
            ref_url = api_url(bmp_db.source_git_ref)
        webservice = webservice_for_person(
            bmp_db.registrant, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        ref = webservice.get(ref_url).jsonBody()
        landing_targets = webservice.get(
            ref["landing_targets_collection_link"]).jsonBody()
        self.assertEqual(1, len(landing_targets["entries"]))
        self.assertThat(
            landing_targets["entries"][0]["self_link"], EndsWith(bmp_url))

    def test_landing_targets_constant_queries(self):
        project = self.factory.makeProduct()
        with person_logged_in(project.owner):
            [source] = self.factory.makeGitRefs(target=project)
            source_url = api_url(source)
            webservice = webservice_for_person(
                project.owner, permission=OAuthPermission.WRITE_PRIVATE)

        def create_mp():
            with admin_logged_in():
                [ref] = self.factory.makeGitRefs(
                    target=project,
                    information_type=InformationType.PRIVATESECURITY)
                self.factory.makeBranchMergeProposalForGit(
                    source_ref=source, target_ref=ref)

        def list_mps():
            webservice.get(source_url + "/landing_targets")

        list_mps()
        recorder1, recorder2 = record_two_runs(list_mps, create_mp, 2)
        self.assertThat(recorder1, HasQueryCount(LessThan(30)))
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))

    def test_dependent_landings(self):
        [ref] = self.factory.makeGitRefs()
        bmp_db = self.factory.makeBranchMergeProposalForGit(
            prerequisite_ref=ref)
        with person_logged_in(bmp_db.registrant):
            bmp_url = api_url(bmp_db)
            ref_url = api_url(ref)
        webservice = webservice_for_person(
            bmp_db.registrant, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        ref = webservice.get(ref_url).jsonBody()
        dependent_landings = webservice.get(
            ref["dependent_landings_collection_link"]).jsonBody()
        self.assertEqual(1, len(dependent_landings["entries"]))
        self.assertThat(
            dependent_landings["entries"][0]["self_link"], EndsWith(bmp_url))
