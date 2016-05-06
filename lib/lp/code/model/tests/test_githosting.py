# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for `GitHostingClient`.

We don't currently do integration testing against a real hosting service,
but we at least check that we're sending the right requests.
"""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from contextlib import contextmanager
import json

from httmock import (
    all_requests,
    HTTMock,
    )
from testtools.matchers import MatchesStructure
from zope.component import getUtility
from zope.interface import implementer
from zope.security.proxy import removeSecurityProxy

from lp.code.errors import (
    GitRepositoryCreationFault,
    GitRepositoryDeletionFault,
    GitRepositoryScanFault,
    )
from lp.code.interfaces.githosting import IGitHostingClient
from lp.services.job.interfaces.job import (
    IRunnableJob,
    JobStatus,
    )
from lp.services.job.model.job import Job
from lp.services.job.runner import (
    BaseRunnableJob,
    JobRunner,
    )
from lp.services.timeout import (
    get_default_timeout_function,
    set_default_timeout_function,
    )
from lp.services.webapp.url import urlappend
from lp.testing import TestCase
from lp.testing.layers import ZopelessDatabaseLayer


class TestGitHostingClient(TestCase):

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestGitHostingClient, self).setUp()
        self.client = getUtility(IGitHostingClient)
        self.endpoint = removeSecurityProxy(self.client).endpoint
        self.request = None

    @contextmanager
    def mockRequests(self, status_code=200, content=b"",
                     set_default_timeout=True):
        @all_requests
        def handler(url, request):
            self.assertIsNone(self.request)
            self.request = request
            return {"status_code": status_code, "content": content}

        with HTTMock(handler):
            original_timeout_function = get_default_timeout_function()
            if set_default_timeout:
                set_default_timeout_function(lambda: 60.0)
            try:
                yield
            finally:
                set_default_timeout_function(original_timeout_function)

    def assertRequest(self, url_suffix, json_data=None, **kwargs):
        self.assertThat(self.request, MatchesStructure.byEquality(
            url=urlappend(self.endpoint, url_suffix), **kwargs))
        if json_data is not None:
            self.assertEqual(json_data, json.loads(self.request.body))

    def test_create(self):
        with self.mockRequests():
            self.client.create("123")
        self.assertRequest(
            "repo", method="POST", json_data={"repo_path": "123"})

    def test_create_clone_from(self):
        with self.mockRequests():
            self.client.create("123", clone_from="122")
        self.assertRequest(
            "repo", method="POST",
            json_data={"repo_path": "123", "clone_from": "122"})

    def test_create_failure(self):
        with self.mockRequests(status_code=400, content=b"Bad request"):
            self.assertRaisesWithContent(
                GitRepositoryCreationFault,
                "Failed to create Git repository: Bad request",
                self.client.create, "123")

    def test_getProperties(self):
        with self.mockRequests(
                content=b'{"default_branch": "refs/heads/master"}'):
            props = self.client.getProperties("123")
        self.assertEqual({"default_branch": "refs/heads/master"}, props)
        self.assertRequest("repo/123", method="GET")

    def test_getProperties_failure(self):
        with self.mockRequests(status_code=400, content=b"Bad request"):
            self.assertRaisesWithContent(
                GitRepositoryScanFault,
                "Failed to get properties of Git repository: Bad request",
                self.client.getProperties, "123")

    def test_setProperties(self):
        with self.mockRequests():
            self.client.setProperties("123", default_branch="refs/heads/a")
        self.assertRequest(
            "repo/123", method="PATCH",
            json_data={"default_branch": "refs/heads/a"})

    def test_setProperties_failure(self):
        with self.mockRequests(status_code=400, content=b"Bad request"):
            self.assertRaisesWithContent(
                GitRepositoryScanFault,
                "Failed to set properties of Git repository: Bad request",
                self.client.setProperties, "123",
                default_branch="refs/heads/a")

    def test_getRefs(self):
        with self.mockRequests(content=b'{"refs/heads/master": {}}'):
            refs = self.client.getRefs("123")
        self.assertEqual({"refs/heads/master": {}}, refs)
        self.assertRequest("repo/123/refs", method="GET")

    def test_getRefs_failure(self):
        with self.mockRequests(status_code=400, content=b"Bad request"):
            self.assertRaisesWithContent(
                GitRepositoryScanFault,
                "Failed to get refs from Git repository: Bad request",
                self.client.getRefs, "123")

    def test_getCommits(self):
        with self.mockRequests(content=b'[{"sha1": "0"}]'):
            commits = self.client.getCommits("123", ["0"])
        self.assertEqual([{"sha1": "0"}], commits)
        self.assertRequest(
            "repo/123/commits", method="POST", json_data={"commits": ["0"]})

    def test_getCommits_failure(self):
        with self.mockRequests(status_code=400, content=b"Bad request"):
            self.assertRaisesWithContent(
                GitRepositoryScanFault,
                "Failed to get commit details from Git repository: "
                "Bad request",
                self.client.getCommits, "123", ["0"])

    def test_getMergeDiff(self):
        with self.mockRequests(content=b'{"patch": ""}'):
            diff = self.client.getMergeDiff("123", "a", "b")
        self.assertEqual({"patch": ""}, diff)
        self.assertRequest("repo/123/compare-merge/a:b", method="GET")

    def test_getMergeDiff_prerequisite(self):
        with self.mockRequests(content=b'{"patch": ""}'):
            diff = self.client.getMergeDiff("123", "a", "b", prerequisite="c")
        self.assertEqual({"patch": ""}, diff)
        self.assertRequest(
            "repo/123/compare-merge/a:b?sha1_prerequisite=c", method="GET")

    def test_getMergeDiff_failure(self):
        with self.mockRequests(status_code=400, content=b"Bad request"):
            self.assertRaisesWithContent(
                GitRepositoryScanFault,
                "Failed to get merge diff from Git repository: Bad request",
                self.client.getMergeDiff, "123", "a", "b")

    def test_detectMerges(self):
        with self.mockRequests(content=b'{"b": "0"}'):
            merges = self.client.detectMerges("123", "a", ["b", "c"])
        self.assertEqual({"b": "0"}, merges)
        self.assertRequest(
            "repo/123/detect-merges/a", method="POST",
            json_data={"sources": ["b", "c"]})

    def test_detectMerges_failure(self):
        with self.mockRequests(status_code=400, content=b"Bad request"):
            self.assertRaisesWithContent(
                GitRepositoryScanFault,
                "Failed to detect merges in Git repository: Bad request",
                self.client.detectMerges, "123", "a", ["b", "c"])

    def test_delete(self):
        with self.mockRequests():
            self.client.delete("123")
        self.assertRequest("repo/123", method="DELETE")

    def test_delete_failed(self):
        with self.mockRequests(status_code=400, content=b"Bad request"):
            self.assertRaisesWithContent(
                GitRepositoryDeletionFault,
                "Failed to delete Git repository: Bad request",
                self.client.delete, "123")

    def test_getBlob(self):
        blob = b''.join(chr(i) for i in range(256))
        content = {"data": blob.encode("base64"), "size": len(blob)}
        with self.mockRequests(content=json.dumps(content)):
            response = self.client.getBlob("123", "dir/path/file/name")
        self.assertEqual(blob, response)
        self.assertRequest(
            "repo/123/blob/dir/path/file/name", method="GET")

    def test_getBlob_revision(self):
        blob = b''.join(chr(i) for i in range(256))
        content = {"data": blob.encode("base64"), "size": len(blob)}
        with self.mockRequests(content=json.dumps(content)):
            response = self.client.getBlob("123", "dir/path/file/name", "dev")
        self.assertEqual(blob, response)
        self.assertRequest(
            "repo/123/blob/dir/path/file/name?rev=dev", method="GET")

    def test_getBlob_failure(self):
        with self.mockRequests(status_code=400, content=b"Bad request"):
            self.assertRaisesWithContent(
                GitRepositoryScanFault,
                "Failed to get file from Git repository: Bad request",
                self.client.getBlob, "123", "dir/path/file/name")

    def test_getBlob_url_quoting(self):
        blob = b''.join(chr(i) for i in range(256))
        content = {"data": blob.encode("base64"), "size": len(blob)}
        with self.mockRequests(content=json.dumps(content)):
            self.client.getBlob("123", "dir/+file name?.txt", "+rev/ no?")
        self.assertRequest(
            "repo/123/blob/dir/%2Bfile%20name%3F.txt?rev=%2Brev%2F+no%3F",
            method="GET")

    def test_getBlob_no_data(self):
        with self.mockRequests(content=json.dumps({"size": 1})):
            self.assertRaisesWithContent(
                GitRepositoryScanFault,
                "Failed to get file from Git repository: 'data'",
                self.client.getBlob, "123", "dir/path/file/name")

    def test_getBlob_no_size(self):
        with self.mockRequests(content=json.dumps({"data": "data"})):
            self.assertRaisesWithContent(
                GitRepositoryScanFault,
                "Failed to get file from Git repository: 'size'",
                self.client.getBlob, "123", "dir/path/file/name")

    def test_getBlob_bad_encoding(self):
        content = {"data": "x", "size": 1}
        with self.mockRequests(content=json.dumps(content)):
            self.assertRaisesWithContent(
                GitRepositoryScanFault,
                "Failed to get file from Git repository: Incorrect padding",
                self.client.getBlob, "123", "dir/path/file/name")

    def test_getBlob_wrong_size(self):
        blob = b''.join(chr(i) for i in range(256))
        content = {"data": blob.encode("base64"), "size": 0}
        with self.mockRequests(content=json.dumps(content)):
            self.assertRaisesWithContent(
                GitRepositoryScanFault,
                "Failed to get file from Git repository: Unexpected size"
                " (256 vs 0)",
                self.client.getBlob, "123", "dir/path/file/name")

    def test_works_in_job(self):
        # `GitHostingClient` is usable from a running job.
        @implementer(IRunnableJob)
        class GetRefsJob(BaseRunnableJob):
            def __init__(self, testcase):
                super(GetRefsJob, self).__init__()
                self.job = Job()
                self.testcase = testcase

            def run(self):
                with self.testcase.mockRequests(
                        content=b'{"refs/heads/master": {}}',
                        set_default_timeout=False):
                    self.refs = self.testcase.client.getRefs("123")

        job = GetRefsJob(self)
        JobRunner([job]).runAll()
        self.assertEqual(JobStatus.COMPLETED, job.job.status)
        self.assertEqual({"refs/heads/master": {}}, job.refs)
        self.assertRequest("repo/123/refs", method="GET")
