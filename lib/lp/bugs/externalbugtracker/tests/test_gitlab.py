# Copyright 2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the GitLab Issues BugTracker."""

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
from lp.bugs.externalbugtracker import get_external_bugtracker
from lp.bugs.externalbugtracker.gitlab import (
    BadGitLabURL,
    GitLab,
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


class TestGitLab(TestCase):

    layer = ZopelessLayer

    def setUp(self):
        super(TestGitLab, self).setUp()
        self.sample_bugs = [
            {"id": 101, "iid": 1, "state": "opened", "labels": []},
            {"id": 102, "iid": 2, "state": "opened", "labels": ["feature"]},
            {"id": 103, "iid": 3, "state": "opened",
             "labels": ["feature", "ui"]},
            {"id": 104, "iid": 4, "state": "closed", "labels": []},
            {"id": 105, "iid": 5, "state": "closed", "labels": ["feature"]},
            ]

    def test_implements_interface(self):
        self.assertTrue(verifyObject(
            IExternalBugTracker,
            GitLab("https://gitlab.com/user/repository/issues")))

    def test_requires_issues_url(self):
        self.assertRaises(
            BadGitLabURL, GitLab, "https://gitlab.com/user/repository")

    @responses.activate
    def test__getPage_authenticated(self):
        responses.add(
            "GET", "https://gitlab.com/api/v4/projects/user%2Frepository/test",
            json="success")
        self.pushConfig(
            "checkwatches.credentials", **{"gitlab.com.token": "sosekrit"})
        tracker = GitLab("https://gitlab.com/user/repository/issues")
        self.assertEqual("success", tracker._getPage("test").json())
        requests = [call.request for call in responses.calls]
        self.assertThat(requests, MatchesListwise([
            MatchesStructure(
                path_url=Equals("/api/v4/projects/user%2Frepository/test"),
                headers=ContainsDict({"Private-Token": Equals("sosekrit")})),
            ]))

    @responses.activate
    def test__getPage_unauthenticated(self):
        responses.add(
            "GET", "https://gitlab.com/api/v4/projects/user%2Frepository/test",
            json="success")
        tracker = GitLab("https://gitlab.com/user/repository/issues")
        self.assertEqual("success", tracker._getPage("test").json())
        requests = [call.request for call in responses.calls]
        self.assertThat(requests, MatchesListwise([
            MatchesStructure(
                path_url=Equals("/api/v4/projects/user%2Frepository/test"),
                headers=Not(Contains("Private-Token"))),
            ]))

    @responses.activate
    def test_getRemoteBug(self):
        responses.add(
            "GET",
            "https://gitlab.com/api/v4/projects/user%2Frepository/issues/1",
            json=self.sample_bugs[0])
        tracker = GitLab("https://gitlab.com/user/repository/issues")
        self.assertEqual((1, self.sample_bugs[0]), tracker.getRemoteBug("1"))
        self.assertEqual(
            "https://gitlab.com/api/v4/projects/user%2Frepository/issues/1",
            responses.calls[-1].request.url)

    def _addIssuesResponse(self):
        responses.add(
            "GET",
            "https://gitlab.com/api/v4/projects/user%2Frepository/issues",
            json=self.sample_bugs)

    @responses.activate
    def test_getRemoteBugBatch(self):
        self._addIssuesResponse()
        tracker = GitLab("https://gitlab.com/user/repository/issues")
        self.assertEqual(
            {bug["iid"]: bug for bug in self.sample_bugs[:2]},
            tracker.getRemoteBugBatch(["1", "2"]))
        self.assertEqual(
            "https://gitlab.com/api/v4/projects/user%2Frepository/issues?"
            "iids[]=1&iids[]=2",
            responses.calls[-1].request.url)

    @responses.activate
    def test_getRemoteBugBatch_last_accessed(self):
        self._addIssuesResponse()
        tracker = GitLab("https://gitlab.com/user/repository/issues")
        since = datetime(2015, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
        self.assertEqual(
            {bug["iid"]: bug for bug in self.sample_bugs[:2]},
            tracker.getRemoteBugBatch(["1", "2"], last_accessed=since))
        self.assertEqual(
            "https://gitlab.com/api/v4/projects/user%2Frepository/issues?"
            "updated_after=2015-01-01T12%3A00%3A00Z&iids[]=1&iids[]=2",
            responses.calls[-1].request.url)

    @responses.activate
    def test_getRemoteBugBatch_caching(self):
        self._addIssuesResponse()
        tracker = GitLab("https://gitlab.com/user/repository/issues")
        tracker.initializeRemoteBugDB(
            [str(bug["iid"]) for bug in self.sample_bugs])
        responses.reset()
        self.assertEqual(
            {bug["iid"]: bug for bug in self.sample_bugs[:2]},
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

        responses.add_callback(
            "GET",
            "https://gitlab.com/api/v4/projects/user%2Frepository/issues",
            callback=issues_callback, content_type="application/json")
        tracker = GitLab("https://gitlab.com/user/repository/issues")
        self.assertEqual(
            {bug["iid"]: bug for bug in self.sample_bugs},
            tracker.getRemoteBugBatch(
                [str(bug["iid"]) for bug in self.sample_bugs]))
        expected_urls = [
            "https://gitlab.com/api/v4/projects/user%2Frepository/issues?" +
            "&".join("iids[]=%s" % bug["iid"] for bug in self.sample_bugs),
            "https://gitlab.com/api/v4/projects/user%2Frepository/issues?"
            "page=2",
            "https://gitlab.com/api/v4/projects/user%2Frepository/issues?"
            "page=3",
            ]
        self.assertEqual(
            expected_urls, [call.request.url for call in responses.calls])

    @responses.activate
    def test_status_opened(self):
        self.sample_bugs = [
            {"id": 101, "iid": 1, "state": "opened", "labels": []},
            # Labels do not affect status, even if names collide.
            {"id": 102, "iid": 2, "state": "opened",
             "labels": ["feature", "closed"]},
            ]
        self._addIssuesResponse()
        tracker = GitLab("https://gitlab.com/user/repository/issues")
        tracker.initializeRemoteBugDB(["1", "2"])
        remote_status = tracker.getRemoteStatus("1")
        self.assertEqual("opened", remote_status)
        lp_status = tracker.convertRemoteStatus(remote_status)
        self.assertEqual(BugTaskStatus.NEW, lp_status)
        remote_status = tracker.getRemoteStatus("2")
        self.assertEqual("opened feature closed", remote_status)
        lp_status = tracker.convertRemoteStatus(remote_status)
        self.assertEqual(BugTaskStatus.NEW, lp_status)

    @responses.activate
    def test_status_closed(self):
        self.sample_bugs = [
            {"id": 101, "iid": 1, "state": "closed", "labels": []},
            # Labels do not affect status, even if names collide.
            {"id": 102, "iid": 2, "state": "closed",
             "labels": ["feature", "opened"]},
            ]
        self._addIssuesResponse()
        tracker = GitLab("https://gitlab.com/user/repository/issues")
        tracker.initializeRemoteBugDB(["1", "2"])
        remote_status = tracker.getRemoteStatus("1")
        self.assertEqual("closed", remote_status)
        lp_status = tracker.convertRemoteStatus(remote_status)
        self.assertEqual(BugTaskStatus.FIXRELEASED, lp_status)
        remote_status = tracker.getRemoteStatus("2")
        self.assertEqual("closed feature opened", remote_status)
        lp_status = tracker.convertRemoteStatus(remote_status)
        self.assertEqual(BugTaskStatus.FIXRELEASED, lp_status)


class TestGitLabUpdateBugWatches(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    @responses.activate
    def test_process_one(self):
        remote_bug = [
            {"id": "12345", "iid": 1234, "state": "opened", "labels": []},
            ]
        responses.add(
            "GET",
            "https://gitlab.com/api/v4/projects/user%2Frepository/issues?"
            "iids[]=1234",
            json=remote_bug, match_querystring=True)
        bug = self.factory.makeBug()
        bug_tracker = self.factory.makeBugTracker(
            base_url="https://gitlab.com/user/repository/issues",
            bugtrackertype=BugTrackerType.GITLAB)
        bug.addWatch(
            bug_tracker, "1234", getUtility(ILaunchpadCelebrities).janitor)
        self.assertEqual(
            [("1234", None)],
            [(watch.remotebug, watch.remotestatus)
             for watch in bug_tracker.watches])
        transaction.commit()
        logger = BufferLogger()
        bug_watch_updater = CheckwatchesMaster(transaction, logger=logger)
        gitlab = get_external_bugtracker(bug_tracker)
        bug_watch_updater.updateBugWatches(gitlab, bug_tracker.watches)
        self.assertEqual(
            "INFO Updating 1 watches for 1 bugs on "
            "https://gitlab.com/api/v4/projects/user%2Frepository\n",
            logger.getLogBuffer())
        self.assertEqual(
            [("1234", BugTaskStatus.NEW)],
            [(watch.remotebug, gitlab.convertRemoteStatus(watch.remotestatus))
             for watch in bug_tracker.watches])

    @responses.activate
    def test_process_many(self):
        remote_bugs = [
            {"id": bug_id + 1, "iid": bug_id,
             "state": "opened" if (bug_id % 2) == 0 else "closed",
             "labels": []}
            for bug_id in range(1000, 1010)]
        responses.add(
            "GET",
            "https://gitlab.com/api/v4/projects/user%2Frepository/issues",
            json=remote_bugs)
        bug = self.factory.makeBug()
        bug_tracker = self.factory.makeBugTracker(
            base_url="https://gitlab.com/user/repository/issues",
            bugtrackertype=BugTrackerType.GITLAB)
        for remote_bug in remote_bugs:
            bug.addWatch(
                bug_tracker, str(remote_bug["iid"]),
                getUtility(ILaunchpadCelebrities).janitor)
        transaction.commit()
        logger = BufferLogger()
        bug_watch_updater = CheckwatchesMaster(transaction, logger=logger)
        gitlab = get_external_bugtracker(bug_tracker)
        bug_watch_updater.updateBugWatches(gitlab, bug_tracker.watches)
        self.assertEqual(
            "INFO Updating 10 watches for 10 bugs on "
            "https://gitlab.com/api/v4/projects/user%2Frepository\n",
            logger.getLogBuffer())
        self.assertContentEqual(
            [(str(bug_id), BugTaskStatus.NEW)
             for bug_id in (1000, 1002, 1004, 1006, 1008)] +
            [(str(bug_id), BugTaskStatus.FIXRELEASED)
             for bug_id in (1001, 1003, 1005, 1007, 1009)],
            [(watch.remotebug, gitlab.convertRemoteStatus(watch.remotestatus))
             for watch in bug_tracker.watches])
