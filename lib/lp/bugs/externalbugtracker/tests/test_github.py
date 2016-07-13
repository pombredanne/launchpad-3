# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the GitHub Issues BugTracker."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from datetime import datetime
import json
from urlparse import (
    parse_qs,
    urlunsplit,
    )

from httmock import (
    HTTMock,
    urlmatch,
    )
import pytz
import transaction
from zope.component import getUtility

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.bugs.externalbugtracker import (
    BugTrackerConnectError,
    get_external_bugtracker,
    )
from lp.bugs.externalbugtracker.github import (
    BadGitHubURL,
    GitHub,
    GitHubExceededRateLimit,
    IGitHubRateLimit,
    )
from lp.bugs.interfaces.bugtask import BugTaskStatus
from lp.bugs.interfaces.bugtracker import BugTrackerType
from lp.bugs.interfaces.externalbugtracker import IExternalBugTracker
from lp.bugs.scripts.checkwatches import CheckwatchesMaster
from lp.services.log.logger import BufferLogger
from lp.testing import (
    TestCase,
    TestCaseWithFactory,
    verifyObject,
    )
from lp.testing.layers import (
    ZopelessDatabaseLayer,
    ZopelessLayer,
    )


class TestGitHubRateLimit(TestCase):

    layer = ZopelessLayer

    def setUp(self):
        super(TestGitHubRateLimit, self).setUp()
        self.rate_limit = getUtility(IGitHubRateLimit)
        self.addCleanup(self.rate_limit.clearCache)

    @urlmatch(path=r"^/rate_limit$")
    def _rate_limit_handler(self, url, request):
        self.rate_limit_request = request
        self.rate_limit_headers = request.headers
        return {
            "status_code": 200,
            "content": {"resources": {"core": self.initial_rate_limit}},
            }

    @urlmatch(path=r"^/$")
    def _target_handler(self, url, request):
        self.target_request = request
        return {"status_code": 200, "content": b"test"}

    def test_makeRequest_no_token(self):
        self.initial_rate_limit = {
            "limit": 60, "remaining": 50, "reset": 1000000000}
        with HTTMock(self._rate_limit_handler, self._target_handler):
            response = self.rate_limit.makeRequest(
                "GET", "http://example.org/")
        self.assertNotIn("Authorization", self.rate_limit_headers)
        self.assertEqual(b"test", response.content)
        limit = self.rate_limit._limits[("example.org", None)]
        self.assertEqual(49, limit["remaining"])
        self.assertEqual(1000000000, limit["reset"])

        limit["remaining"] = 0
        self.rate_limit_request = None
        with HTTMock(self._rate_limit_handler, self._target_handler):
            self.assertRaisesWithContent(
                GitHubExceededRateLimit,
                "Rate limit for example.org exceeded "
                "(resets at Sun Sep  9 07:16:40 2001)",
                self.rate_limit.makeRequest,
                "GET", "http://example.org/")
        self.assertIsNone(self.rate_limit_request)
        self.assertEqual(0, limit["remaining"])

    def test_makeRequest_check_token(self):
        self.initial_rate_limit = {
            "limit": 5000, "remaining": 4000, "reset": 1000000000}
        with HTTMock(self._rate_limit_handler, self._target_handler):
            response = self.rate_limit.makeRequest(
                "GET", "http://example.org/", token="abc")
        self.assertEqual("token abc", self.rate_limit_headers["Authorization"])
        self.assertEqual(b"test", response.content)
        limit = self.rate_limit._limits[("example.org", "abc")]
        self.assertEqual(3999, limit["remaining"])
        self.assertEqual(1000000000, limit["reset"])

        limit["remaining"] = 0
        self.rate_limit_request = None
        with HTTMock(self._rate_limit_handler, self._target_handler):
            self.assertRaisesWithContent(
                GitHubExceededRateLimit,
                "Rate limit for example.org exceeded "
                "(resets at Sun Sep  9 07:16:40 2001)",
                self.rate_limit.makeRequest,
                "GET", "http://example.org/", token="abc")
        self.assertIsNone(self.rate_limit_request)
        self.assertEqual(0, limit["remaining"])

    def test_makeRequest_check_503(self):
        @urlmatch(path=r"^/rate_limit$")
        def rate_limit_handler(url, request):
            return {"status_code": 503}

        with HTTMock(rate_limit_handler):
            self.assertRaises(
                BugTrackerConnectError, self.rate_limit.makeRequest,
                "GET", "http://example.org/")


class TestGitHub(TestCase):

    layer = ZopelessLayer

    def setUp(self):
        super(TestGitHub, self).setUp()
        self.addCleanup(getUtility(IGitHubRateLimit).clearCache)
        self.sample_bugs = [
            {"id": 1, "state": "open", "labels": []},
            {"id": 2, "state": "open", "labels": [{"name": "feature"}]},
            {"id": 3, "state": "open",
             "labels": [{"name": "feature"}, {"name": "ui"}]},
            {"id": 4, "state": "closed", "labels": []},
            {"id": 5, "state": "closed", "labels": [{"name": "feature"}]},
            ]

    def test_implements_interface(self):
        self.assertTrue(verifyObject(
            IExternalBugTracker,
            GitHub("https://github.com/user/repository/issues")))

    def test_requires_issues_url(self):
        self.assertRaises(
            BadGitHubURL, GitHub, "https://github.com/user/repository")

    @urlmatch(path=r"^/rate_limit$")
    def _rate_limit_handler(self, url, request):
        self.rate_limit_request = request
        rate_limit = {"limit": 5000, "remaining": 4000, "reset": 1000000000}
        return {
            "status_code": 200,
            "content": {"resources": {"core": rate_limit}},
            }

    def test_getRemoteBug(self):
        @urlmatch(path=r".*/issues/1$")
        def handler(url, request):
            self.request = request
            return {"status_code": 200, "content": self.sample_bugs[0]}

        tracker = GitHub("https://github.com/user/repository/issues")
        with HTTMock(self._rate_limit_handler, handler):
            self.assertEqual(
                (1, self.sample_bugs[0]), tracker.getRemoteBug("1"))
        self.assertEqual(
            "https://api.github.com/repos/user/repository/issues/1",
            self.request.url)

    @urlmatch(path=r".*/issues$")
    def _issues_handler(self, url, request):
        self.issues_request = request
        return {"status_code": 200, "content": json.dumps(self.sample_bugs)}

    def test_getRemoteBugBatch(self):
        tracker = GitHub("https://github.com/user/repository/issues")
        with HTTMock(self._rate_limit_handler, self._issues_handler):
            self.assertEqual(
                {bug["id"]: bug for bug in self.sample_bugs[:2]},
                tracker.getRemoteBugBatch(["1", "2"]))
        self.assertEqual(
            "https://api.github.com/repos/user/repository/issues?state=all",
            self.issues_request.url)

    def test_getRemoteBugBatch_last_accessed(self):
        tracker = GitHub("https://github.com/user/repository/issues")
        since = datetime(2015, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
        with HTTMock(self._rate_limit_handler, self._issues_handler):
            self.assertEqual(
                {bug["id"]: bug for bug in self.sample_bugs[:2]},
                tracker.getRemoteBugBatch(["1", "2"], last_accessed=since))
        self.assertEqual(
            "https://api.github.com/repos/user/repository/issues?"
            "state=all&since=2015-01-01T12%3A00%3A00Z",
            self.issues_request.url)

    def test_getRemoteBugBatch_caching(self):
        tracker = GitHub("https://github.com/user/repository/issues")
        with HTTMock(self._rate_limit_handler, self._issues_handler):
            tracker.initializeRemoteBugDB(
                [str(bug["id"]) for bug in self.sample_bugs])
            self.issues_request = None
            self.assertEqual(
                {bug["id"]: bug for bug in self.sample_bugs[:2]},
                tracker.getRemoteBugBatch(["1", "2"]))
            self.assertIsNone(self.issues_request)

    def test_getRemoteBugBatch_pagination(self):
        @urlmatch(path=r".*/issues")
        def handler(url, request):
            self.issues_requests.append(request)
            base_url = urlunsplit(list(url[:3]) + ["", ""])
            page = int(parse_qs(url.query).get("page", ["1"])[0])
            links = []
            if page != 3:
                links.append('<%s?page=%d>; rel="next"' % (base_url, page + 1))
                links.append('<%s?page=3>; rel="last"' % base_url)
            if page != 1:
                links.append('<%s?page=1>; rel="first"' % base_url)
                links.append('<%s?page=%d>; rel="prev"' % (base_url, page - 1))
            start = (page - 1) * 2
            end = page * 2
            return {
                "status_code": 200,
                "headers": {"Link": ", ".join(links)},
                "content": json.dumps(self.sample_bugs[start:end]),
                }

        self.issues_requests = []
        tracker = GitHub("https://github.com/user/repository/issues")
        with HTTMock(self._rate_limit_handler, handler):
            self.assertEqual(
                {bug["id"]: bug for bug in self.sample_bugs},
                tracker.getRemoteBugBatch(
                    [str(bug["id"]) for bug in self.sample_bugs]))
        expected_urls = [
            "https://api.github.com/repos/user/repository/issues?state=all",
            "https://api.github.com/repos/user/repository/issues?page=2",
            "https://api.github.com/repos/user/repository/issues?page=3",
            ]
        self.assertEqual(
            expected_urls, [request.url for request in self.issues_requests])

    def test_status_open(self):
        self.sample_bugs = [
            {"id": 1, "state": "open", "labels": []},
            # Labels do not affect status, even if names collide.
            {"id": 2, "state": "open",
             "labels": [{"name": "feature"}, {"name": "closed"}]},
            ]
        tracker = GitHub("https://github.com/user/repository/issues")
        with HTTMock(self._rate_limit_handler, self._issues_handler):
            tracker.initializeRemoteBugDB(["1", "2"])
        remote_status = tracker.getRemoteStatus("1")
        self.assertEqual("open", remote_status)
        lp_status = tracker.convertRemoteStatus(remote_status)
        self.assertEqual(BugTaskStatus.NEW, lp_status)
        remote_status = tracker.getRemoteStatus("2")
        self.assertEqual("open feature closed", remote_status)
        lp_status = tracker.convertRemoteStatus(remote_status)
        self.assertEqual(BugTaskStatus.NEW, lp_status)

    def test_status_closed(self):
        self.sample_bugs = [
            {"id": 1, "state": "closed", "labels": []},
            # Labels do not affect status, even if names collide.
            {"id": 2, "state": "closed",
             "labels": [{"name": "feature"}, {"name": "open"}]},
            ]
        tracker = GitHub("https://github.com/user/repository/issues")
        with HTTMock(self._rate_limit_handler, self._issues_handler):
            tracker.initializeRemoteBugDB(["1", "2"])
        remote_status = tracker.getRemoteStatus("1")
        self.assertEqual("closed", remote_status)
        lp_status = tracker.convertRemoteStatus(remote_status)
        self.assertEqual(BugTaskStatus.FIXRELEASED, lp_status)
        remote_status = tracker.getRemoteStatus("2")
        self.assertEqual("closed feature open", remote_status)
        lp_status = tracker.convertRemoteStatus(remote_status)
        self.assertEqual(BugTaskStatus.FIXRELEASED, lp_status)


class TestGitHubUpdateBugWatches(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    @urlmatch(path=r"^/rate_limit$")
    def _rate_limit_handler(self, url, request):
        self.rate_limit_request = request
        rate_limit = {"limit": 5000, "remaining": 4000, "reset": 1000000000}
        return {
            "status_code": 200,
            "content": {"resources": {"core": rate_limit}},
            }

    def test_process_one(self):
        remote_bug = {"id": 1234, "state": "open", "labels": []}

        @urlmatch(path=r".*/issues/1234$")
        def handler(url, request):
            return {"status_code": 200, "content": remote_bug}

        bug = self.factory.makeBug()
        bug_tracker = self.factory.makeBugTracker(
            base_url="https://github.com/user/repository/issues",
            bugtrackertype=BugTrackerType.GITHUB)
        bug.addWatch(
            bug_tracker, "1234", getUtility(ILaunchpadCelebrities).janitor)
        self.assertEqual(
            [("1234", None)],
            [(watch.remotebug, watch.remotestatus)
             for watch in bug_tracker.watches])
        transaction.commit()
        logger = BufferLogger()
        bug_watch_updater = CheckwatchesMaster(transaction, logger=logger)
        github = get_external_bugtracker(bug_tracker)
        with HTTMock(self._rate_limit_handler, handler):
            bug_watch_updater.updateBugWatches(github, bug_tracker.watches)
        self.assertEqual(
            "INFO Updating 1 watches for 1 bugs on "
            "https://api.github.com/repos/user/repository\n",
            logger.getLogBuffer())
        self.assertEqual(
            [("1234", BugTaskStatus.NEW)],
            [(watch.remotebug, github.convertRemoteStatus(watch.remotestatus))
             for watch in bug_tracker.watches])

    def test_process_many(self):
        remote_bugs = [
            {"id": bug_id,
             "state": "open" if (bug_id % 2) == 0 else "closed",
             "labels": []}
            for bug_id in range(1000, 1010)]

        @urlmatch(path=r".*/issues$")
        def handler(url, request):
            return {"status_code": 200, "content": json.dumps(remote_bugs)}

        bug = self.factory.makeBug()
        bug_tracker = self.factory.makeBugTracker(
            base_url="https://github.com/user/repository/issues",
            bugtrackertype=BugTrackerType.GITHUB)
        for remote_bug in remote_bugs:
            bug.addWatch(
                bug_tracker, str(remote_bug["id"]),
                getUtility(ILaunchpadCelebrities).janitor)
        transaction.commit()
        logger = BufferLogger()
        bug_watch_updater = CheckwatchesMaster(transaction, logger=logger)
        github = get_external_bugtracker(bug_tracker)
        with HTTMock(self._rate_limit_handler, handler):
            bug_watch_updater.updateBugWatches(github, bug_tracker.watches)
        self.assertEqual(
            "INFO Updating 10 watches for 10 bugs on "
            "https://api.github.com/repos/user/repository\n",
            logger.getLogBuffer())
        self.assertContentEqual(
            [(str(bug_id), BugTaskStatus.NEW)
             for bug_id in (1000, 1002, 1004, 1006, 1008)] +
            [(str(bug_id), BugTaskStatus.FIXRELEASED)
             for bug_id in (1001, 1003, 1005, 1007, 1009)],
            [(watch.remotebug, github.convertRemoteStatus(watch.remotestatus))
             for watch in bug_tracker.watches])
