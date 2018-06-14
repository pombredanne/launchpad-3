# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for `BranchHostingClient`.

We don't currently do integration testing against a real hosting service,
but we at least check that we're sending the right requests.
"""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from contextlib import contextmanager
import re

from lazr.restful.utils import get_current_browser_request
import responses
from testtools.matchers import MatchesStructure
from zope.component import getUtility
from zope.interface import implementer
from zope.security.proxy import removeSecurityProxy

from lp.code.errors import (
    BranchFileNotFound,
    BranchHostingFault,
    )
from lp.code.interfaces.branchhosting import IBranchHostingClient
from lp.services.job.interfaces.job import (
    IRunnableJob,
    JobStatus,
    )
from lp.services.job.model.job import Job
from lp.services.job.runner import (
    BaseRunnableJob,
    JobRunner,
    )
from lp.services.timeline.requesttimeline import get_request_timeline
from lp.services.timeout import (
    get_default_timeout_function,
    set_default_timeout_function,
    )
from lp.services.webapp.url import urlappend
from lp.testing import TestCase
from lp.testing.layers import ZopelessDatabaseLayer


class TestBranchHostingClient(TestCase):

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestBranchHostingClient, self).setUp()
        self.client = getUtility(IBranchHostingClient)
        self.endpoint = removeSecurityProxy(self.client).endpoint
        self.requests = []

    @contextmanager
    def mockRequests(self, method, set_default_timeout=True, **kwargs):
        with responses.RequestsMock() as requests_mock:
            requests_mock.add(method, re.compile(r".*"), **kwargs)
            original_timeout_function = get_default_timeout_function()
            if set_default_timeout:
                set_default_timeout_function(lambda: 60.0)
            try:
                yield
            finally:
                set_default_timeout_function(original_timeout_function)
            self.requests = [call.request for call in requests_mock.calls]

    def assertRequest(self, url_suffix, **kwargs):
        [request] = self.requests
        self.assertThat(request, MatchesStructure.byEquality(
            url=urlappend(self.endpoint, url_suffix), method="GET", **kwargs))
        timeline = get_request_timeline(get_current_browser_request())
        action = timeline.actions[-1]
        self.assertEqual("branch-hosting-get", action.category)
        self.assertEqual(
            "/" + url_suffix.split("?", 1)[0], action.detail.split(" ", 1)[0])

    def test_getDiff(self):
        with self.mockRequests("GET", body="---\n+++\n"):
            diff = self.client.getDiff("~owner/project/branch", "2", "1")
        self.assertEqual(b"---\n+++\n", diff)
        self.assertRequest("~owner/project/branch/diff/2/1")

    def test_getDiff_no_old_revision(self):
        with self.mockRequests("GET", body="---\n+++\n"):
            diff = self.client.getDiff("~owner/project/branch", "2")
        self.assertEqual(b"---\n+++\n", diff)
        self.assertRequest("~owner/project/branch/diff/2")

    def test_getDiff_context_lines(self):
        with self.mockRequests("GET", body="---\n+++\n"):
            diff = self.client.getDiff(
                "~owner/project/branch", "2", "1", context_lines=4)
        self.assertEqual(b"---\n+++\n", diff)
        self.assertRequest("~owner/project/branch/diff/2/1?context_lines=4")

    def test_getDiff_failure(self):
        with self.mockRequests("GET", status=400):
            self.assertRaisesWithContent(
                BranchHostingFault,
                "Failed to get diff from Bazaar branch: "
                "400 Client Error: Bad Request",
                self.client.getDiff, "~owner/project/branch", "2", "1")

    def test_getInventory(self):
        with self.mockRequests("GET", json={"filelist": []}):
            response = self.client.getInventory(
                "~owner/project/branch", "dir/path/file/name")
        self.assertEqual({"filelist": []}, response)
        self.assertRequest(
            "~owner/project/branch/+json/files/head%3A/dir/path/file/name")

    def test_getInventory_revision(self):
        with self.mockRequests("GET", json={"filelist": []}):
            response = self.client.getInventory(
                "~owner/project/branch", "dir/path/file/name", rev="a")
        self.assertEqual({"filelist": []}, response)
        self.assertRequest(
            "~owner/project/branch/+json/files/a/dir/path/file/name")

    def test_getInventory_not_found(self):
        with self.mockRequests("GET", status=404):
            self.assertRaisesWithContent(
                BranchFileNotFound,
                "Branch ~owner/project/branch has no file dir/path/file/name",
                self.client.getInventory,
                "~owner/project/branch", "dir/path/file/name")

    def test_getInventory_revision_not_found(self):
        with self.mockRequests("GET", status=404):
            self.assertRaisesWithContent(
                BranchFileNotFound,
                "Branch ~owner/project/branch has no file dir/path/file/name "
                "at revision a",
                self.client.getInventory,
                "~owner/project/branch", "dir/path/file/name", rev="a")

    def test_getInventory_failure(self):
        with self.mockRequests("GET", status=400):
            self.assertRaisesWithContent(
                BranchHostingFault,
                "Failed to get inventory from Bazaar branch: "
                "400 Client Error: Bad Request",
                self.client.getInventory,
                "~owner/project/branch", "dir/path/file/name")

    def test_getInventory_url_quoting(self):
        with self.mockRequests("GET", json={"filelist": []}):
            self.client.getInventory(
                "~owner/project/branch", "+file/ name?", rev="+rev/ id?")
        self.assertRequest(
            "~owner/project/branch/+json/"
            "files/%2Brev%2F%20id%3F/%2Bfile/%20name%3F")

    def test_getBlob(self):
        blob = b"".join(chr(i) for i in range(256))
        with self.mockRequests("GET", body=blob):
            response = self.client.getBlob("~owner/project/branch", "file-id")
        self.assertEqual(blob, response)
        self.assertRequest("~owner/project/branch/download/head%3A/file-id")

    def test_getBlob_revision(self):
        blob = b"".join(chr(i) for i in range(256))
        with self.mockRequests("GET", body=blob):
            response = self.client.getBlob(
                "~owner/project/branch", "file-id", rev="a")
        self.assertEqual(blob, response)
        self.assertRequest("~owner/project/branch/download/a/file-id")

    def test_getBlob_not_found(self):
        with self.mockRequests("GET", status=404):
            self.assertRaisesWithContent(
                BranchFileNotFound,
                "Branch ~owner/project/branch has no file with ID file-id",
                self.client.getBlob, "~owner/project/branch", "file-id")

    def test_getBlob_revision_not_found(self):
        with self.mockRequests("GET", status=404):
            self.assertRaisesWithContent(
                BranchFileNotFound,
                "Branch ~owner/project/branch has no file with ID file-id "
                "at revision a",
                self.client.getBlob,
                "~owner/project/branch", "file-id", rev="a")

    def test_getBlob_failure(self):
        with self.mockRequests("GET", status=400):
            self.assertRaisesWithContent(
                BranchHostingFault,
                "Failed to get file from Bazaar branch: "
                "400 Client Error: Bad Request",
                self.client.getBlob, "~owner/project/branch", "file-id")

    def test_getBlob_url_quoting(self):
        blob = b"".join(chr(i) for i in range(256))
        with self.mockRequests("GET", body=blob):
            self.client.getBlob(
                "~owner/project/branch", "+file/ id?", rev="+rev/ id?")
        self.assertRequest(
            "~owner/project/branch/"
            "download/%2Brev%2F%20id%3F/%2Bfile%2F%20id%3F")

    def test_works_in_job(self):
        # `BranchHostingClient` is usable from a running job.
        blob = b"".join(chr(i) for i in range(256))

        @implementer(IRunnableJob)
        class GetBlobJob(BaseRunnableJob):
            def __init__(self, testcase):
                super(GetBlobJob, self).__init__()
                self.job = Job()
                self.testcase = testcase

            def run(self):
                with self.testcase.mockRequests(
                        "GET", body=blob, set_default_timeout=False):
                    self.blob = self.testcase.client.getBlob(
                        "~owner/project/branch", "file-id")
                # We must make this assertion inside the job, since the job
                # runner creates a separate timeline.
                self.testcase.assertRequest(
                    "~owner/project/branch/download/head%3A/file-id")

        job = GetBlobJob(self)
        JobRunner([job]).runAll()
        self.assertEqual(JobStatus.COMPLETED, job.job.status)
        self.assertEqual(blob, job.blob)
