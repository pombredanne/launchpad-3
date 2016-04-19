# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for `GitHostingClient`.

We don't currently do integration testing against a real hosting service,
but we at least check that we're sending the right requests.
"""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from fixtures import MonkeyPatch
import requests
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.code.errors import (
    GitRepositoryCreationFault,
    GitRepositoryDeletionFault,
    GitRepositoryScanFault,
    )
from lp.code.interfaces.githosting import IGitHostingClient
from lp.services.timeout import URLFetcher
from lp.services.webapp.url import urlappend
from lp.testing import TestCase
from lp.testing.fakemethod import FakeMethod
from lp.testing.layers import LaunchpadZopelessLayer


class TestGitHostingClient(TestCase):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestGitHostingClient, self).setUp()
        self.client = getUtility(IGitHostingClient)
        self.endpoint = removeSecurityProxy(self.client).endpoint
        self.session = URLFetcher()._makeSession()
        response = requests.Response()
        response.status_code = 200
        response._content = b""
        self.session.request = FakeMethod(result=response)
        self.useFixture(MonkeyPatch(
            "lp.services.timeout.URLFetcher._makeSession",
            lambda _, trust_env=None: self.session))

    def assertCalled(self, *args, **kwargs):
        self.assertEqual([(args, kwargs)], self.session.request.calls)

    def test_create(self):
        self.client.create("123")
        self.assertCalled(
            url=urlappend(self.endpoint, "repo"), method="post",
            json={"repo_path": "123"})

    def test_create_clone_from(self):
        self.client.create("123", clone_from="122")
        self.assertCalled(
            url=urlappend(self.endpoint, "repo"), method="post",
            json={"repo_path": "123", "clone_from": "122"})

    def test_create_failure(self):
        self.session.request.result.status_code = 400
        self.session.request.result._content = b"Bad request"
        self.assertRaisesWithContent(
            GitRepositoryCreationFault,
            "Failed to create Git repository: Bad request",
            self.client.create, "123")

    def test_getProperties(self):
        self.session.request.result._content = (
            b'{"default_branch": "refs/heads/master"}')
        props = self.client.getProperties("123")
        self.assertEqual({"default_branch": "refs/heads/master"}, props)
        self.assertCalled(
            url=urlappend(self.endpoint, "repo/123"), method="get")

    def test_getProperties_failure(self):
        self.session.request.result.status_code = 400
        self.session.request.result._content = b"Bad request"
        self.assertRaisesWithContent(
            GitRepositoryScanFault,
            "Failed to get properties of Git repository: Bad request",
            self.client.getProperties, "123")

    def test_setProperties(self):
        self.client.setProperties("123", default_branch="refs/heads/a")
        self.assertCalled(
            url=urlappend(self.endpoint, "repo/123"), method="patch",
            json={"default_branch": "refs/heads/a"})

    def test_setProperties_failure(self):
        self.session.request.result.status_code = 400
        self.session.request.result._content = b"Bad request"
        self.assertRaisesWithContent(
            GitRepositoryScanFault,
            "Failed to set properties of Git repository: Bad request",
            self.client.setProperties, "123", default_branch="refs/heads/a")

    def test_getRefs(self):
        self.session.request.result._content = b'{"refs/heads/master": {}}'
        refs = self.client.getRefs("123")
        self.assertEqual({"refs/heads/master": {}}, refs)
        self.assertCalled(
            url=urlappend(self.endpoint, "repo/123/refs"), method="get")

    def test_getRefs_failure(self):
        self.session.request.result.status_code = 400
        self.session.request.result._content = b"Bad request"
        self.assertRaisesWithContent(
            GitRepositoryScanFault,
            "Failed to get refs from Git repository: Bad request",
            self.client.getRefs, "123")

    def test_getCommits(self):
        self.session.request.result._content = b'[{"sha1": "0"}]'
        commits = self.client.getCommits("123", ["0"])
        self.assertEqual([{"sha1": "0"}], commits)
        self.assertCalled(
            url=urlappend(self.endpoint, "repo/123/commits"), method="post",
            json={"commits": ["0"]})

    def test_getCommits_failure(self):
        self.session.request.result.status_code = 400
        self.session.request.result._content = b"Bad request"
        self.assertRaisesWithContent(
            GitRepositoryScanFault,
            "Failed to get commit details from Git repository: Bad request",
            self.client.getCommits, "123", ["0"])

    def test_getMergeDiff(self):
        self.session.request.result._content = b'{"patch": ""}'
        diff = self.client.getMergeDiff("123", "a", "b")
        self.assertEqual({"patch": ""}, diff)
        self.assertCalled(
            url=urlappend(self.endpoint, "repo/123/compare-merge/a:b"),
            method="get")

    def test_getMergeDiff_prerequisite(self):
        self.session.request.result._content = b'{"patch": ""}'
        diff = self.client.getMergeDiff("123", "a", "b", prerequisite="c")
        self.assertEqual({"patch": ""}, diff)
        expected_url = urlappend(
            self.endpoint, "repo/123/compare-merge/a:b?sha1_prerequisite=c")
        self.assertCalled(url=expected_url, method="get")

    def test_getMergeDiff_failure(self):
        self.session.request.result.status_code = 400
        self.session.request.result._content = b"Bad request"
        self.assertRaisesWithContent(
            GitRepositoryScanFault,
            "Failed to get merge diff from Git repository: Bad request",
            self.client.getMergeDiff, "123", "a", "b")

    def test_detectMerges(self):
        self.session.request.result._content = b'{"b": "0"}'
        merges = self.client.detectMerges("123", "a", ["b", "c"])
        self.assertEqual({"b": "0"}, merges)
        self.assertCalled(
            url=urlappend(self.endpoint, "repo/123/detect-merges/a"),
            method="post", json={"sources": ["b", "c"]})

    def test_detectMerges_failure(self):
        self.session.request.result.status_code = 400
        self.session.request.result._content = b"Bad request"
        self.assertRaisesWithContent(
            GitRepositoryScanFault,
            "Failed to detect merges in Git repository: Bad request",
            self.client.detectMerges, "123", "a", ["b", "c"])

    def test_delete(self):
        self.client.delete("123")
        self.assertCalled(
            url=urlappend(self.endpoint, "repo/123"), method="delete")

    def test_delete_failed(self):
        self.session.request.result.status_code = 400
        self.session.request.result._content = b"Bad request"
        self.assertRaisesWithContent(
            GitRepositoryDeletionFault,
            "Failed to delete Git repository: Bad request",
            self.client.delete, "123")
