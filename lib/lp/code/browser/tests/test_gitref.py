# Copyright 2015-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for GitRefView."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from datetime import datetime
import hashlib
import re

from fixtures import FakeLogger
import pytz
import soupmatchers
from storm.store import Store
from testtools.matchers import (
    Equals,
    Not,
    )
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.code.interfaces.gitjob import IGitRefScanJobSource
from lp.code.interfaces.gitrepository import IGitRepositorySet
from lp.code.tests.helpers import GitHostingFixture
from lp.services.beautifulsoup import BeautifulSoup
from lp.services.job.runner import JobRunner
from lp.services.timeout import TimeoutError
from lp.services.utils import seconds_since_epoch
from lp.services.webapp.publisher import canonical_url
from lp.testing import (
    admin_logged_in,
    BrowserTestCase,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.dbuser import dbuser
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing.matchers import HasQueryCount
from lp.testing.pages import (
    extract_text,
    find_tags_by_class,
    )
from lp.testing.views import (
    create_initialized_view,
    create_view,
    )


class TestGitRefNavigation(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_canonical_url_branch(self):
        [ref] = self.factory.makeGitRefs(paths=["refs/heads/master"])
        self.assertEqual(
            "%s/+ref/master" % canonical_url(ref.repository),
            canonical_url(ref))

    def test_canonical_url_with_slash(self):
        [ref] = self.factory.makeGitRefs(paths=["refs/heads/with/slash"])
        self.assertEqual(
            "%s/+ref/with/slash" % canonical_url(ref.repository),
            canonical_url(ref))

    def test_canonical_url_percent_encoded(self):
        [ref] = self.factory.makeGitRefs(paths=["refs/heads/with#hash"])
        self.assertEqual(
            "%s/+ref/with%%23hash" % canonical_url(ref.repository),
            canonical_url(ref))

    def test_canonical_url_non_ascii(self):
        [ref] = self.factory.makeGitRefs(paths=["refs/heads/\N{SNOWMAN}"])
        self.assertEqual(
            "%s/+ref/%%E2%%98%%83" % canonical_url(ref.repository),
            canonical_url(ref))

    def test_canonical_url_tag(self):
        [ref] = self.factory.makeGitRefs(paths=["refs/tags/1.0"])
        self.assertEqual(
            "%s/+ref/refs/tags/1.0" % canonical_url(ref.repository),
            canonical_url(ref))


class MissingCommitsNote(soupmatchers.Tag):

    def __init__(self):
        super(MissingCommitsNote, self).__init__(
            "missing commits note", "div",
            text="Some recent commit information could not be fetched.")


class TestGitRefView(BrowserTestCase):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestGitRefView, self).setUp()
        self.hosting_fixture = self.useFixture(GitHostingFixture())

    def _test_rendering(self, branch_name):
        repository = self.factory.makeGitRepository(
            owner=self.factory.makePerson(name="person"),
            target=self.factory.makeProduct(name="target"),
            name="git")
        getUtility(IGitRepositorySet).setDefaultRepositoryForOwner(
            repository.owner, repository.target, repository, repository.owner)
        [ref] = self.factory.makeGitRefs(
            repository=repository, paths=["refs/heads/%s" % branch_name])
        view = create_view(ref, "+index")
        # To test the breadcrumbs we need a correct traversal stack.
        view.request.traversed_objects = [repository, ref, view]
        view.initialize()
        breadcrumbs_tag = soupmatchers.Tag(
            'breadcrumbs', 'ol', attrs={'class': 'breadcrumbs'})
        self.assertThat(
            view(),
            soupmatchers.HTMLContains(
                soupmatchers.Within(
                    breadcrumbs_tag,
                    soupmatchers.Tag(
                        'git collection breadcrumb', 'a',
                        text='Git',
                        attrs={'href': re.compile(r'/\+git$')})),
                soupmatchers.Within(
                    breadcrumbs_tag,
                    soupmatchers.Tag(
                        'repository breadcrumb', 'a',
                        text='lp:~person/target',
                        attrs={'href': re.compile(
                            r'/~person/target/\+git/git')})),
                soupmatchers.Within(
                    breadcrumbs_tag,
                    soupmatchers.Tag(
                        'git ref breadcrumb', 'li',
                        text=re.compile(r'\s%s\s' % branch_name)))))

    def test_rendering(self):
        self._test_rendering("master")

    def test_rendering_non_ascii(self):
        self._test_rendering("\N{SNOWMAN}")

    def test_clone_instructions(self):
        [ref] = self.factory.makeGitRefs(paths=["refs/heads/branch"])
        username = ref.owner.name
        text = self.getMainText(ref, "+index", user=ref.owner)
        self.assertTextMatchesExpressionIgnoreWhitespace(r"""
            git clone -b branch https://git.launchpad.dev/.*
            git clone -b branch git\+ssh://{username}@git.launchpad.dev/.*
            """.format(username=username), text)

    def makeCommitLog(self):
        authors = [self.factory.makePerson() for _ in range(5)]
        with admin_logged_in():
            author_emails = [author.preferredemail.email for author in authors]
        dates = [
            datetime(2015, 1, day + 1, tzinfo=pytz.UTC) for day in range(5)]
        return [
            {
                "sha1": unicode(hashlib.sha1(str(i)).hexdigest()),
                "message": "Commit %d" % i,
                "author": {
                    "name": authors[i].display_name,
                    "email": author_emails[i],
                    "time": int(seconds_since_epoch(dates[i])),
                    },
                "committer": {
                    "name": authors[i].display_name,
                    "email": author_emails[i],
                    "time": int(seconds_since_epoch(dates[i])),
                    },
                "parents": [unicode(hashlib.sha1(str(i - 1)).hexdigest())],
                "tree": unicode(hashlib.sha1("").hexdigest()),
                }
            for i in range(5)]

    def scanRef(self, ref, tip):
        self.hosting_fixture.getRefs.result = {
            ref.path: {"object": {"sha1": tip["sha1"], "type": "commit"}},
            }
        self.hosting_fixture.getCommits.result = [tip]
        self.hosting_fixture.getProperties.result = {
            "default_branch": ref.path,
            }
        job = getUtility(IGitRefScanJobSource).create(
            removeSecurityProxy(ref.repository))
        with dbuser("branchscanner"):
            JobRunner([job]).runAll()

    def test_recent_commits(self):
        [ref] = self.factory.makeGitRefs(paths=["refs/heads/branch"])
        log = self.makeCommitLog()
        self.hosting_fixture.getLog.result = list(reversed(log))
        self.scanRef(ref, log[-1])
        view = create_initialized_view(ref, "+index")
        contents = view()
        expected_texts = list(reversed([
            "%.7s...\nby\n%s\non 2015-01-%02d" % (
                log[i]["sha1"], log[i]["author"]["name"], i + 1)
            for i in range(5)]))
        details = find_tags_by_class(contents, "commit-details")
        self.assertEqual(
            expected_texts, [extract_text(detail) for detail in details])
        expected_urls = list(reversed([
            "https://git.launchpad.dev/%s/commit/?id=%s" % (
                ref.repository.shortened_path, log[i]["sha1"])
            for i in range(5)]))
        self.assertEqual(
            expected_urls, [detail.a["href"] for detail in details])
        self.assertThat(
            contents, Not(soupmatchers.HTMLContains(MissingCommitsNote())))

    def test_recent_commits_with_merge(self):
        [ref] = self.factory.makeGitRefs(paths=["refs/heads/branch"])
        log = self.makeCommitLog()
        self.hosting_fixture.getLog.result = list(reversed(log))
        self.scanRef(ref, log[-1])
        mp = self.factory.makeBranchMergeProposalForGit(target_ref=ref)
        merged_tip = dict(log[-1])
        merged_tip["sha1"] = unicode(hashlib.sha1("merged").hexdigest())
        self.scanRef(mp.merge_source, merged_tip)
        mp.markAsMerged(merged_revision_id=log[0]["sha1"])
        view = create_initialized_view(ref, "+index")
        contents = view()
        soup = BeautifulSoup(contents)
        details = soup.findAll(
            attrs={"class": re.compile(r"commit-details|commit-comment")})
        expected_texts = list(reversed([
            "%.7s...\nby\n%s\non 2015-01-%02d" % (
                log[i]["sha1"], log[i]["author"]["name"], i + 1)
            for i in range(5)]))
        expected_texts.append(
            "Merged branch\n%s" % mp.merge_source.display_name)
        self.assertEqual(
            expected_texts, [extract_text(detail) for detail in details])
        self.assertEqual(
            [canonical_url(mp), canonical_url(mp.merge_source)],
            [link["href"] for link in details[5].findAll("a")])
        self.assertThat(
            contents, Not(soupmatchers.HTMLContains(MissingCommitsNote())))

    def test_recent_commits_with_merge_from_deleted_ref(self):
        [ref] = self.factory.makeGitRefs(paths=["refs/heads/branch"])
        log = self.makeCommitLog()
        self.hosting_fixture.getLog.result = list(reversed(log))
        self.scanRef(ref, log[-1])
        mp = self.factory.makeBranchMergeProposalForGit(target_ref=ref)
        merged_tip = dict(log[-1])
        merged_tip["sha1"] = unicode(hashlib.sha1("merged").hexdigest())
        self.scanRef(mp.merge_source, merged_tip)
        mp.markAsMerged(merged_revision_id=log[0]["sha1"])
        mp.source_git_repository.removeRefs([mp.source_git_path])
        view = create_initialized_view(ref, "+index")
        contents = view()
        soup = BeautifulSoup(contents)
        details = soup.findAll(
            attrs={"class": re.compile(r"commit-details|commit-comment")})
        expected_texts = list(reversed([
            "%.7s...\nby\n%s\non 2015-01-%02d" % (
                log[i]["sha1"], log[i]["author"]["name"], i + 1)
            for i in range(5)]))
        expected_texts.append(
            "Merged branch\n%s" % mp.merge_source.display_name)
        self.assertEqual(
            expected_texts, [extract_text(detail) for detail in details])
        self.assertEqual(
            [canonical_url(mp)],
            [link["href"] for link in details[5].findAll("a")])
        self.assertThat(
            contents, Not(soupmatchers.HTMLContains(MissingCommitsNote())))

    def _test_all_commits_link(self, branch_name, encoded_branch_name=None):
        if encoded_branch_name is None:
            encoded_branch_name = branch_name
        [ref] = self.factory.makeGitRefs(paths=["refs/heads/%s" % branch_name])
        log = self.makeCommitLog()
        self.hosting_fixture.getLog.result = list(reversed(log))
        self.scanRef(ref, log[-1])
        view = create_initialized_view(ref, "+index")
        recent_commits_tag = soupmatchers.Tag(
            'recent commits', 'div', attrs={'id': 'recent-commits'})
        expected_url = (
            'https://git.launchpad.dev/%s/log/?h=%s' %
            (ref.repository.shortened_path, encoded_branch_name))
        self.assertThat(
            view(),
            soupmatchers.HTMLContains(
                soupmatchers.Within(
                    recent_commits_tag,
                    soupmatchers.Tag(
                        'all commits link', 'a', text='All commits',
                        attrs={'href': expected_url}))))

    def test_all_commits_link(self):
        self._test_all_commits_link("branch")

    def test_all_commits_link_non_ascii(self):
        self._test_all_commits_link("\N{SNOWMAN}", "%E2%98%83")

    def test_query_count_landing_candidates(self):
        project = self.factory.makeProduct()
        [ref] = self.factory.makeGitRefs(target=project)
        for i in range(10):
            self.factory.makeBranchMergeProposalForGit(target_ref=ref)
        [source] = self.factory.makeGitRefs(target=project)
        [prereq] = self.factory.makeGitRefs(target=project)
        self.factory.makeBranchMergeProposalForGit(
            source_ref=source, target_ref=ref, prerequisite_ref=prereq)
        Store.of(ref).flush()
        Store.of(ref).invalidate()
        view = create_view(ref, '+index')
        with StormStatementRecorder() as recorder:
            view.landing_candidates
        self.assertThat(recorder, HasQueryCount(Equals(12)))

    def test_query_count_landing_targets(self):
        project = self.factory.makeProduct()
        [ref] = self.factory.makeGitRefs(target=project)
        for i in range(10):
            self.factory.makeBranchMergeProposalForGit(source_ref=ref)
        [target] = self.factory.makeGitRefs(target=project)
        [prereq] = self.factory.makeGitRefs(target=project)
        self.factory.makeBranchMergeProposalForGit(
            source_ref=ref, target_ref=target, prerequisite_ref=prereq)
        Store.of(ref).flush()
        Store.of(ref).invalidate()
        view = create_view(ref, '+index')
        with StormStatementRecorder() as recorder:
            view.landing_targets
        self.assertThat(recorder, HasQueryCount(Equals(12)))

    def test_timeout(self):
        # The page renders even if fetching commits times out.
        self.useFixture(FakeLogger())
        [ref] = self.factory.makeGitRefs()
        log = self.makeCommitLog()
        self.scanRef(ref, log[-1])
        self.hosting_fixture.getLog.failure = TimeoutError
        view = create_initialized_view(ref, "+index")
        contents = view()
        soup = BeautifulSoup(contents)
        details = soup.findAll(
            attrs={"class": re.compile(r"commit-details|commit-comment")})
        expected_text = "%.7s...\nby\n%s\non 2015-01-%02d" % (
            log[-1]["sha1"], log[-1]["author"]["name"], len(log))
        self.assertEqual(
            [expected_text], [extract_text(detail) for detail in details])
        self.assertThat(
            contents, soupmatchers.HTMLContains(MissingCommitsNote()))
