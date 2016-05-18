# Copyright 2015-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Git references."""

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
    MatchesListwise,
    MatchesStructure,
    )
from zope.component import getUtility

from lp.app.enums import InformationType
from lp.app.interfaces.informationtype import IInformationType
from lp.app.interfaces.launchpad import IPrivacy
from lp.code.interfaces.githosting import IGitHostingClient
from lp.services.config import config
from lp.services.features.testing import FeatureFixture
from lp.services.memcache.interfaces import IMemcacheClient
from lp.services.webapp.interfaces import OAuthPermission
from lp.testing import (
    admin_logged_in,
    ANONYMOUS,
    api_url,
    person_logged_in,
    TestCaseWithFactory,
    verifyObject,
    )
from lp.testing.fakemethod import FakeMethod
from lp.testing.fixture import ZopeUtilityFixture
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing.pages import webservice_for_person


class TestGitRef(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_display_name(self):
        [master, personal] = self.factory.makeGitRefs(
            paths=[u"refs/heads/master", u"refs/heads/people/foo/bar"])
        repo_path = master.repository.shortened_path
        self.assertEqual(
            [u"%s:master" % repo_path, "%s:people/foo/bar" % repo_path],
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
                u"sha1": self.sha1_tip,
                u"message": u"tip",
                u"author": {
                    u"name": self.authors[0].display_name,
                    u"email": self.author_emails[0],
                    u"time": int((self.dates[1] - epoch).total_seconds()),
                    },
                u"committer": {
                    u"name": self.authors[1].display_name,
                    u"email": self.author_emails[1],
                    u"time": int((self.dates[1] - epoch).total_seconds()),
                    },
                u"parents": [self.sha1_root],
                u"tree": unicode(hashlib.sha1("").hexdigest()),
                },
            {
                u"sha1": self.sha1_root,
                u"message": u"root",
                u"author": {
                    u"name": self.authors[1].display_name,
                    u"email": self.author_emails[1],
                    u"time": int((self.dates[0] - epoch).total_seconds()),
                    },
                u"committer": {
                    u"name": self.authors[0].display_name,
                    u"email": self.author_emails[0],
                    u"time": int((self.dates[0] - epoch).total_seconds()),
                    },
                u"parents": [],
                u"tree": unicode(hashlib.sha1("").hexdigest()),
                },
            ]
        self.hosting_client = FakeMethod()
        self.hosting_client.getLog = FakeMethod(result=self.log)
        self.useFixture(
            ZopeUtilityFixture(self.hosting_client, IGitHostingClient))

    def test_basic(self):
        commits = self.ref.getCommits(self.sha1_tip)
        path = self.ref.repository.getInternalPath()
        self.assertEqual(
            [((path, self.sha1_tip),
              {"limit": None, "stop": None, "logger": None})],
            self.hosting_client.getLog.calls)
        self.assertThat(commits, MatchesListwise([
            ContainsDict({
                "sha1": Equals(self.sha1_tip),
                "author": MatchesStructure.byEquality(person=self.authors[0]),
                "author_date": Equals(self.dates[1]),
                "commit_message": Equals(u"tip"),
                }),
            ContainsDict({
                "sha1": Equals(self.sha1_root),
                "author": MatchesStructure.byEquality(person=self.authors[1]),
                "author_date": Equals(self.dates[0]),
                "commit_message": Equals(u"root"),
                }),
            ]))
        key = u"%s:git-log:%s:%s" % (config.instance_name, path, self.sha1_tip)
        self.assertEqual(
            json.dumps(self.log),
            getUtility(IMemcacheClient).get(key.encode("UTF-8")))

    def test_cache(self):
        path = self.ref.repository.getInternalPath()
        key = u"%s:git-log:%s:%s" % (config.instance_name, path, self.sha1_tip)
        getUtility(IMemcacheClient).set(key.encode("UTF-8"), "[]")
        self.assertEqual([], self.ref.getCommits(self.sha1_tip))

    def test_disable_hosting(self):
        self.useFixture(
            FeatureFixture({u"code.git.log.disable_hosting": u"on"}))
        commits = self.ref.getCommits(self.sha1_tip)
        self.assertThat(commits, MatchesListwise([
            ContainsDict({
                "sha1": Equals(self.ref.commit_sha1),
                "commit_message": Is(None),
                }),
            ]))
        self.assertEqual([], self.hosting_client.getLog.calls)
        path = self.ref.repository.getInternalPath()
        key = u"%s:git-log:%s:%s" % (config.instance_name, path, self.sha1_tip)
        self.assertIsNone(getUtility(IMemcacheClient).get(key.encode("UTF-8")))

    def test_disable_memcache(self):
        self.useFixture(
            FeatureFixture({u"code.git.log.disable_memcache": u"on"}))
        path = self.ref.repository.getInternalPath()
        key = u"%s:git-log:%s:%s" % (config.instance_name, path, self.sha1_tip)
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
            self.hosting_client.getLog.calls)
        key = u"%s:git-log:%s:%s:limit=10:stop=%s" % (
            config.instance_name, path, self.sha1_tip, self.sha1_root)
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
        key = u"%s:git-log:%s:%s" % (config.instance_name, path, self.sha1_tip)
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


class TestGitRefWebservice(TestCaseWithFactory):
    """Tests for the webservice."""

    layer = DatabaseFunctionalLayer

    def test_attributes(self):
        [master] = self.factory.makeGitRefs(paths=[u"refs/heads/master"])
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
        self.assertEqual(u"refs/heads/master", result["path"])
        self.assertEqual(
            unicode(hashlib.sha1(u"refs/heads/master").hexdigest()),
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
