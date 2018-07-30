# Copyright 2010-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the externalbugtracker package."""

__metaclass__ = type

import responses
from testtools.matchers import (
    ContainsDict,
    Equals,
    MatchesListwise,
    MatchesStructure,
    )
import transaction
from zope.interface import implementer

from lp.bugs.externalbugtracker.base import (
    BugTrackerConnectError,
    ExternalBugTracker,
    LP_USER_AGENT,
    )
from lp.bugs.externalbugtracker.debbugs import DebBugs
from lp.bugs.interfaces.externalbugtracker import (
    ISupportsBackLinking,
    ISupportsCommentImport,
    ISupportsCommentPushing,
    )
from lp.testing import TestCase
from lp.testing.layers import ZopelessDatabaseLayer


@implementer(ISupportsBackLinking)
class BackLinkingExternalBugTracker(ExternalBugTracker):
    pass


@implementer(ISupportsCommentImport)
class CommentImportingExternalBugTracker(ExternalBugTracker):
    pass


@implementer(ISupportsCommentPushing)
class CommentPushingExternalBugTracker(ExternalBugTracker):
    pass


class TestCheckwatchesConfig(TestCase):

    layer = ZopelessDatabaseLayer
    base_url = "http://www.example.com/"

    def test_sync_comments_enabled(self):
        # If the global config checkwatches.sync_comments is True,
        # external bug trackers will set their sync_comments attribute
        # according to their support of comment syncing.
        self.pushConfig('checkwatches', sync_comments=True)
        # A plain tracker will never support syncing comments.
        tracker = ExternalBugTracker(self.base_url)
        self.assertFalse(tracker.sync_comments)
        # Trackers that support comment pushing, comment pulling or
        # back-linking will have sync_comments set to True.
        tracker = BackLinkingExternalBugTracker(self.base_url)
        self.assertTrue(tracker.sync_comments)
        tracker = CommentImportingExternalBugTracker(self.base_url)
        self.assertTrue(tracker.sync_comments)
        tracker = CommentPushingExternalBugTracker(self.base_url)
        self.assertTrue(tracker.sync_comments)

    def test_sync_comments_disabled(self):
        # If the global config checkwatches.sync_comments is False,
        # external bug trackers will always set their sync_comments
        # attribute to False.
        self.pushConfig('checkwatches', sync_comments=False)
        tracker = ExternalBugTracker(self.base_url)
        self.assertFalse(tracker.sync_comments)
        tracker = BackLinkingExternalBugTracker(self.base_url)
        self.assertFalse(tracker.sync_comments)
        tracker = CommentImportingExternalBugTracker(self.base_url)
        self.assertFalse(tracker.sync_comments)
        tracker = CommentPushingExternalBugTracker(self.base_url)
        self.assertFalse(tracker.sync_comments)

    def test_sync_debbugs_comments_enabled(self):
        # Debian Bugs syncing can also be switched on and off using a
        # separate config variable, sync_debbugs_comments. DebBugs
        # supports comment pushing and import.
        self.pushConfig(
            'checkwatches', sync_comments=True, sync_debbugs_comments=True)
        tracker = DebBugs(self.base_url)
        self.assertTrue(tracker.sync_comments)
        # When either sync_comments or sync_debbugs_comments is False
        # (or both), the Debian Bugs external bug tracker will claim
        # to not support any form of comment syncing.
        for state in ((True, False), (False, True), (False, False)):
            self.pushConfig(
                'checkwatches', sync_comments=state[0],
                sync_debbugs_comments=state[1])
            tracker = DebBugs(self.base_url)
            self.assertFalse(tracker.sync_comments)

    @responses.activate
    def test_postPage_returns_response_page(self):
        # _postPage posts, then returns the page text it gets back from
        # the server.
        base_url = "http://example.com/"
        form = self.factory.getUniqueString()
        fake_form = "<bugzilla>%s</bugzilla>" % self.factory.getUniqueString()
        bugtracker = ExternalBugTracker(base_url)
        transaction.commit()
        responses.add("POST", base_url + form, body=fake_form)
        self.assertEqual(fake_form, bugtracker._postPage(form, {}).text)

    @responses.activate
    def test_postPage_does_not_repost_on_redirect(self):
        # By default, if the POST redirects, _postPage leaves requests to
        # handle it in the normal, RFC-compliant way.
        base_url = "http://example.com/"
        form = self.factory.getUniqueString()
        target = self.factory.getUniqueString()
        fake_form = "<bugzilla>%s</bugzilla>" % self.factory.getUniqueString()
        bugtracker = ExternalBugTracker(base_url)
        transaction.commit()
        responses.add(
            "POST", base_url + form, status=302,
            headers={"Location": base_url + target})
        responses.add("GET", base_url + target, body=fake_form)

        bugtracker._postPage(form, {})

        requests = [call.request for call in responses.calls]
        self.assertThat(requests, MatchesListwise([
            MatchesStructure.byEquality(method="POST", path_url="/" + form),
            MatchesStructure.byEquality(method="GET", path_url="/" + target),
            ]))

    @responses.activate
    def test_postPage_can_repost_on_redirect(self):
        # Some pages (that means you, BugZilla bug-search page!) can
        # redirect on POST, but without honouring the POST.  Standard
        # requests behaviour is to redirect to a GET, but if the caller
        # says it's safe, _postPage can re-do the POST at the new URL.
        base_url = "http://example.com/"
        form = self.factory.getUniqueString()
        target = self.factory.getUniqueString()
        fake_form = "<bugzilla>%s</bugzilla>" % self.factory.getUniqueString()
        bugtracker = ExternalBugTracker(base_url)
        transaction.commit()
        responses.add(
            "POST", base_url + form, status=302,
            headers={"Location": base_url + target})
        responses.add("POST", base_url + target, body=fake_form)

        bugtracker._postPage(form, form={}, repost_on_redirect=True)

        requests = [call.request for call in responses.calls]
        self.assertThat(requests, MatchesListwise([
            MatchesStructure.byEquality(method="POST", path_url="/" + form),
            MatchesStructure.byEquality(method="POST", path_url="/" + target),
            ]))


class TestExternalBugTracker(TestCase):
    """Tests for various methods of the ExternalBugTracker."""

    layer = ZopelessDatabaseLayer

    @responses.activate
    def test_postPage_raises_on_404(self):
        # When posting, a 404 is converted to a BugTrackerConnectError.
        base_url = "http://example.com/"
        bugtracker = ExternalBugTracker(base_url)
        transaction.commit()
        responses.add("POST", base_url + "some-url", status=404)
        self.assertRaises(
            BugTrackerConnectError,
            bugtracker._postPage, 'some-url', {'post-data': 'here'})

    @responses.activate
    def test_postPage_sends_host(self):
        # When posting, a Host header is sent.
        base_host = 'example.com'
        base_url = 'http://%s/' % base_host
        bugtracker = ExternalBugTracker(base_url)
        transaction.commit()
        responses.add("POST", base_url + "some-url")
        bugtracker._postPage('some-url', {'post-data': 'here'})
        self.assertThat(responses.calls[-1].request, MatchesStructure(
            headers=ContainsDict({
                "User-Agent": Equals(LP_USER_AGENT),
                "Host": Equals(base_host),
                })))
