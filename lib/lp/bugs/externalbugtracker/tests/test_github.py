# Copyright 2016-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the GitHub Issues BugTracker."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from datetime import datetime
import json

import pytz
import responses
from six.moves.urllib_parse import (
    parse_qs,
    urlsplit,
    urlunsplit,
    )
from testtools.matchers import (
    Contains,
    ContainsDict,
    Equals,
    MatchesListwise,
    MatchesStructure,
    Not,
    )
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


def _add_rate_limit_response(host, limit=5000, remaining=4000,
                             reset=1000000000):
    limits = {"limit": limit, "remaining": remaining, "reset": reset}
    responses.add(
        "GET", "https://%s/rate_limit" % host,
        json={"resources": {"core": limits}})


class TestGitHubRateLimit(TestCase):

    layer = ZopelessLayer

    def setUp(self):
        super(TestGitHubRateLimit, self).setUp()
        self.rate_limit = getUtility(IGitHubRateLimit)
        self.addCleanup(self.rate_limit.clearCache)

    @responses.activate
    def test_makeRequest_no_token(self):
        _add_rate_limit_response("example.org", limit=60, remaining=50)
        responses.add("GET", "http://example.org/", body="test")
        response = self.rate_limit.makeRequest("GET", "http://example.org/")
        self.assertThat(responses.calls[0].request, MatchesStructure(
            path_url=Equals("/rate_limit"),
            headers=Not(Contains("Authorization"))))
        self.assertEqual(b"test", response.content)
        limit = self.rate_limit._limits[("example.org", None)]
        self.assertEqual(49, limit["remaining"])
        self.assertEqual(1000000000, limit["reset"])

        limit["remaining"] = 0
        responses.reset()
        self.assertRaisesWithContent(
            GitHubExceededRateLimit,
            "Rate limit for example.org exceeded "
            "(resets at Sun Sep  9 07:16:40 2001)",
            self.rate_limit.makeRequest,
            "GET", "http://example.org/")
        self.assertEqual(0, len(responses.calls))
        self.assertEqual(0, limit["remaining"])

    @responses.activate
    def test_makeRequest_check_token(self):
        _add_rate_limit_response("example.org")
        responses.add("GET", "http://example.org/", body="test")
        response = self.rate_limit.makeRequest(
            "GET", "http://example.org/", token="abc")
        self.assertThat(responses.calls[0].request, MatchesStructure(
            path_url=Equals("/rate_limit"),
            headers=ContainsDict({"Authorization": Equals("token abc")})))
        self.assertEqual(b"test", response.content)
        limit = self.rate_limit._limits[("example.org", "abc")]
        self.assertEqual(3999, limit["remaining"])
        self.assertEqual(1000000000, limit["reset"])

        limit["remaining"] = 0
        responses.reset()
        self.assertRaisesWithContent(
            GitHubExceededRateLimit,
            "Rate limit for example.org exceeded "
            "(resets at Sun Sep  9 07:16:40 2001)",
            self.rate_limit.makeRequest,
            "GET", "http://example.org/", token="abc")
        self.assertEqual(0, len(responses.calls))
        self.assertEqual(0, limit["remaining"])

    @responses.activate
    def test_makeRequest_check_503(self):
        responses.add("GET", "https://example.org/rate_limit", status=503)
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

    @responses.activate
    def test__getPage_authenticated(self):
        _add_rate_limit_response("api.github.com")
        responses.add(
            "GET", "https://api.github.com/repos/user/repository/test",
            json="success")
        self.pushConfig(
            "checkwatches.credentials", **{"api.github.com.token": "sosekrit"})
        tracker = GitHub("https://github.com/user/repository/issues")
        self.assertEqual("success", tracker._getPage("test").json())
        requests = [call.request for call in responses.calls]
        self.assertThat(requests, MatchesListwise([
            MatchesStructure(
                path_url=Equals("/rate_limit"),
                headers=ContainsDict({
                    "Authorization": Equals("token sosekrit"),
                    })),
            MatchesStructure(
                path_url=Equals("/repos/user/repository/test"),
                headers=ContainsDict({
                    "Authorization": Equals("token sosekrit"),
                    })),
            ]))

    @responses.activate
    def test__getPage_unauthenticated(self):
        _add_rate_limit_response("api.github.com")
        responses.add(
            "GET", "https://api.github.com/repos/user/repository/test",
            json="success")
        tracker = GitHub("https://github.com/user/repository/issues")
        self.assertEqual("success", tracker._getPage("test").json())
        requests = [call.request for call in responses.calls]
        self.assertThat(requests, MatchesListwise([
            MatchesStructure(
                path_url=Equals("/rate_limit"),
                headers=Not(Contains("Authorization"))),
            MatchesStructure(
                path_url=Equals("/repos/user/repository/test"),
                headers=Not(Contains("Authorization"))),
            ]))

    @responses.activate
    def test_getRemoteBug(self):
        _add_rate_limit_response("api.github.com")
        responses.add(
            "GET", "https://api.github.com/repos/user/repository/issues/1",
            json=self.sample_bugs[0])
        tracker = GitHub("https://github.com/user/repository/issues")
        self.assertEqual((1, self.sample_bugs[0]), tracker.getRemoteBug("1"))
        self.assertEqual(
            "https://api.github.com/repos/user/repository/issues/1",
            responses.calls[-1].request.url)

    def _addIssuesResponse(self):
        responses.add(
            "GET", "https://api.github.com/repos/user/repository/issues",
            json=self.sample_bugs)

    @responses.activate
    def test_getRemoteBugBatch(self):
        _add_rate_limit_response("api.github.com")
        self._addIssuesResponse()
        tracker = GitHub("https://github.com/user/repository/issues")
        self.assertEqual(
            {bug["id"]: bug for bug in self.sample_bugs[:2]},
            tracker.getRemoteBugBatch(["1", "2"]))
        self.assertEqual(
            "https://api.github.com/repos/user/repository/issues?state=all",
            responses.calls[-1].request.url)

    @responses.activate
    def test_getRemoteBugBatch_last_accessed(self):
        _add_rate_limit_response("api.github.com")
        self._addIssuesResponse()
        tracker = GitHub("https://github.com/user/repository/issues")
        since = datetime(2015, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
        self.assertEqual(
            {bug["id"]: bug for bug in self.sample_bugs[:2]},
            tracker.getRemoteBugBatch(["1", "2"], last_accessed=since))
        self.assertEqual(
            "https://api.github.com/repos/user/repository/issues?"
            "state=all&since=2015-01-01T12%3A00%3A00Z",
            responses.calls[-1].request.url)

    @responses.activate
    def test_getRemoteBugBatch_caching(self):
        _add_rate_limit_response("api.github.com")
        self._addIssuesResponse()
        tracker = GitHub("https://github.com/user/repository/issues")
        tracker.initializeRemoteBugDB(
            [str(bug["id"]) for bug in self.sample_bugs])
        responses.reset()
        self.assertEqual(
            {bug["id"]: bug for bug in self.sample_bugs[:2]},
            tracker.getRemoteBugBatch(["1", "2"]))
        self.assertEqual(0, len(responses.calls))

    @responses.activate
    def test_getRemoteBugBatch_pagination(self):
        def issues_callback(request):
            url = urlsplit(request.url)
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
            return (
                200, {"Link": ", ".join(links)},
                json.dumps(self.sample_bugs[start:end]))

        _add_rate_limit_response("api.github.com")
        responses.add_callback(
            "GET", "https://api.github.com/repos/user/repository/issues",
            callback=issues_callback, content_type="application/json")
        tracker = GitHub("https://github.com/user/repository/issues")
        self.assertEqual(
            {bug["id"]: bug for bug in self.sample_bugs},
            tracker.getRemoteBugBatch(
                [str(bug["id"]) for bug in self.sample_bugs]))
        expected_urls = [
            "https://api.github.com/rate_limit",
            "https://api.github.com/repos/user/repository/issues?state=all",
            "https://api.github.com/repos/user/repository/issues?page=2",
            "https://api.github.com/repos/user/repository/issues?page=3",
            ]
        self.assertEqual(
            expected_urls, [call.request.url for call in responses.calls])

    @responses.activate
    def test_status_open(self):
        self.sample_bugs = [
            {"id": 1, "state": "open", "labels": []},
            # Labels do not affect status, even if names collide.
            {"id": 2, "state": "open",
             "labels": [{"name": "feature"}, {"name": "closed"}]},
            ]
        _add_rate_limit_response("api.github.com")
        self._addIssuesResponse()
        tracker = GitHub("https://github.com/user/repository/issues")
        tracker.initializeRemoteBugDB(["1", "2"])
        remote_status = tracker.getRemoteStatus("1")
        self.assertEqual("open", remote_status)
        lp_status = tracker.convertRemoteStatus(remote_status)
        self.assertEqual(BugTaskStatus.NEW, lp_status)
        remote_status = tracker.getRemoteStatus("2")
        self.assertEqual("open feature closed", remote_status)
        lp_status = tracker.convertRemoteStatus(remote_status)
        self.assertEqual(BugTaskStatus.NEW, lp_status)

    @responses.activate
    def test_status_closed(self):
        self.sample_bugs = [
            {"id": 1, "state": "closed", "labels": []},
            # Labels do not affect status, even if names collide.
            {"id": 2, "state": "closed",
             "labels": [{"name": "feature"}, {"name": "open"}]},
            ]
        _add_rate_limit_response("api.github.com")
        self._addIssuesResponse()
        tracker = GitHub("https://github.com/user/repository/issues")
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

    @responses.activate
    def test_process_one(self):
        remote_bug = {"id": 1234, "state": "open", "labels": []}
        _add_rate_limit_response("api.github.com")
        responses.add(
            "GET", "https://api.github.com/repos/user/repository/issues/1234",
            json=remote_bug)
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
        bug_watch_updater.updateBugWatches(github, bug_tracker.watches)
        self.assertEqual(
            "INFO Updating 1 watches for 1 bugs on "
            "https://api.github.com/repos/user/repository\n",
            logger.getLogBuffer())
        self.assertEqual(
            [("1234", BugTaskStatus.NEW)],
            [(watch.remotebug, github.convertRemoteStatus(watch.remotestatus))
             for watch in bug_tracker.watches])

    @responses.activate
    def test_process_many(self):
        remote_bugs = [
            {"id": bug_id,
             "state": "open" if (bug_id % 2) == 0 else "closed",
             "labels": []}
            for bug_id in range(1000, 1010)]
        _add_rate_limit_response("api.github.com")
        responses.add(
            "GET", "https://api.github.com/repos/user/repository/issues",
            json=remote_bugs)
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
