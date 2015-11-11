# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Git references."""

__metaclass__ = type

import hashlib

from testtools.matchers import EndsWith

from lp.app.enums import InformationType
from lp.app.interfaces.informationtype import IInformationType
from lp.app.interfaces.launchpad import IPrivacy
from lp.services.webapp.interfaces import OAuthPermission
from lp.testing import (
    ANONYMOUS,
    api_url,
    person_logged_in,
    TestCaseWithFactory,
    verifyObject,
    )
from lp.testing.layers import DatabaseFunctionalLayer
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
