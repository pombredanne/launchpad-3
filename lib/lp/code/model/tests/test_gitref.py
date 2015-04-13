# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Git references."""

__metaclass__ = type

import hashlib

from testtools.matchers import EndsWith

from lp.code.interfaces.gitrepository import GIT_FEATURE_FLAG
from lp.services.features.testing import FeatureFixture
from lp.services.webapp.interfaces import OAuthPermission
from lp.testing import (
    ANONYMOUS,
    api_url,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.pages import webservice_for_person


class TestGitRef(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_display_name(self):
        self.useFixture(FeatureFixture({GIT_FEATURE_FLAG: u"on"}))
        [master, personal] = self.factory.makeGitRefs(
            paths=[u"refs/heads/master", u"refs/heads/people/foo/bar"])
        self.assertEqual(
            ["master", "people/foo/bar"],
            [ref.display_name for ref in (master, personal)])


class TestGitRefWebservice(TestCaseWithFactory):
    """Tests for the webservice."""

    layer = DatabaseFunctionalLayer

    def test_attributes(self):
        self.useFixture(FeatureFixture({GIT_FEATURE_FLAG: u"on"}))
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
