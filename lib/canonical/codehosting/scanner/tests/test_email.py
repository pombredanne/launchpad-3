# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for the scanner's email generation."""

__metaclass__ = type

import email
import unittest

# This non-standard import is necessary to hook up the event system.
import zope.component.event
from zope.component import getUtility

from canonical.codehosting.jobs import JobRunner
from canonical.codehosting.scanner.email import send_tip_changed_emails
from canonical.codehosting.scanner.fixture import make_zope_event_fixture
from canonical.codehosting.scanner.tests.test_bzrsync import BzrSyncTestCase
from canonical.launchpad.interfaces import (
    BranchSubscriptionDiffSize, BranchSubscriptionNotificationLevel,
    CodeReviewNotificationLevel, IPersonSet)
from lp.code.interfaces.branchjob import (
    IRevisionMailJobSource, IRevisionsAddedJobSource)
from canonical.launchpad.mail import stub
from canonical.testing import LaunchpadZopelessLayer


class TestBzrSyncEmail(BzrSyncTestCase):
    """Tests BzrSync support for generating branch email notifications."""

    def setUp(self):
        BzrSyncTestCase.setUp(self)
        fixture = make_zope_event_fixture(send_tip_changed_emails)
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        stub.test_emails = []

    def makeDatabaseBranch(self):
        branch = BzrSyncTestCase.makeDatabaseBranch(self)
        LaunchpadZopelessLayer.txn.begin()
        test_user = getUtility(IPersonSet).getByEmail('test@canonical.com')
        branch.subscribe(
            test_user,
            BranchSubscriptionNotificationLevel.FULL,
            BranchSubscriptionDiffSize.FIVEKLINES,
            CodeReviewNotificationLevel.NOEMAIL)
        LaunchpadZopelessLayer.txn.commit()
        return branch

    def assertTextIn(self, expected, text):
        """Assert that expected is in text.

        Report expected and text in case of failure.
        """
        self.failUnless(expected in text, '%r not in %r' % (expected, text))

    def test_empty_branch(self):
        self.makeBzrSync(self.db_branch).syncBranchAndClose()
        JobRunner.fromReady(getUtility(IRevisionMailJobSource)).runAll()
        self.assertEqual(len(stub.test_emails), 1)
        [initial_email] = stub.test_emails
        expected = 'First scan of the branch detected 0 revisions'
        email_body = email.message_from_string(initial_email[2]).get_payload()
        self.assertTextIn(expected, email_body)

    def test_import_revision(self):
        self.commitRevision()
        self.makeBzrSync(self.db_branch).syncBranchAndClose()
        JobRunner.fromReady(getUtility(IRevisionMailJobSource)).runAll()
        self.assertEqual(len(stub.test_emails), 1)
        [initial_email] = stub.test_emails
        expected = ('First scan of the branch detected 1 revision'
                    ' in the revision history of the=\n branch.')
        email_body = email.message_from_string(initial_email[2]).get_payload()
        self.assertTextIn(expected, email_body)

    def test_import_uncommit(self):
        self.commitRevision()
        self.makeBzrSync(self.db_branch).syncBranchAndClose()
        JobRunner.fromReady(getUtility(IRevisionMailJobSource)).runAll()
        stub.test_emails = []
        self.uncommitRevision()
        self.makeBzrSync(self.db_branch).syncBranchAndClose()
        JobRunner.fromReady(getUtility(IRevisionMailJobSource)).runAll()
        self.assertEqual(len(stub.test_emails), 1)
        [uncommit_email] = stub.test_emails
        expected = '1 revision was removed from the branch.'
        email_body = email.message_from_string(
            uncommit_email[2]).get_payload()
        self.assertTextIn(expected, email_body)

    def test_import_recommit(self):
        # When scanning the uncommit and new commit there should be an email
        # generated saying that 1 (in this case) revision has been removed,
        # and another email with the diff and log message.
        self.commitRevision('first')
        self.makeBzrSync(self.db_branch).syncBranchAndClose()
        JobRunner.fromReady(getUtility(IRevisionMailJobSource)).runAll()
        stub.test_emails = []
        self.uncommitRevision()
        self.writeToFile(filename="hello.txt",
                         contents="Hello World\n")
        author = self.factory.getUniqueString()
        self.commitRevision('second', committer=author)
        self.makeBzrSync(self.db_branch).syncBranchAndClose()
        JobRunner.fromReady(getUtility(IRevisionsAddedJobSource)).runAll()
        JobRunner.fromReady(getUtility(IRevisionMailJobSource)).runAll()
        self.assertEqual(len(stub.test_emails), 2)
        [recommit_email, uncommit_email] = stub.test_emails
        uncommit_email_body = uncommit_email[2]
        expected = '1 revision was removed from the branch.'
        self.assertTextIn(expected, uncommit_email_body)
        subject = (
            'Subject: [Branch %s] Test branch' % self.db_branch.unique_name)
        self.assertTextIn(expected, uncommit_email_body)
        recommit_email_body = recommit_email[2]
        body_bits = [
            'Subject: [Branch %s] Rev 1: second'
            % self.db_branch.unique_name,
            'revno: 1',
            'committer: %s' % author,
            'branch nick: %s'  % self.bzr_branch.nick,
            'message:\n  second',
            'added:\n  hello.txt',
            "=3D=3D=3D added file 'hello.txt'",
            ]
        for bit in body_bits:
            self.assertTextIn(bit, recommit_email_body)


class TestBzrSyncNoEmail(BzrSyncTestCase):
    """Tests BzrSync support for not generating branch email notifications
    when no one is interested.
    """

    def setUp(self):
        BzrSyncTestCase.setUp(self)
        stub.test_emails = []

    def assertNoPendingEmails(self):
        jobs = list(getUtility(IRevisionMailJobSource).iterReady())
        jobs.extend(getUtility(IRevisionsAddedJobSource).iterReady())
        self.assertEqual([], jobs, "There should be no pending emails.")

    def test_no_subscribers(self):
        self.assertEqual(self.db_branch.subscribers.count(), 0,
                         "There should be no subscribers to the branch.")

    def test_empty_branch(self):
        bzrsync = self.makeBzrSync(self.db_branch)
        bzrsync.syncBranchAndClose()
        self.assertNoPendingEmails()

    def test_import_revision(self):
        self.commitRevision()
        bzrsync = self.makeBzrSync(self.db_branch)
        bzrsync.syncBranchAndClose()
        self.assertNoPendingEmails()

    def test_import_uncommit(self):
        self.commitRevision()
        bzrsync = self.makeBzrSync(self.db_branch)
        bzrsync.syncBranchAndClose()
        stub.test_emails = []
        self.uncommitRevision()
        bzrsync = self.makeBzrSync(self.db_branch)
        bzrsync.syncBranchAndClose()
        self.assertNoPendingEmails()

    def test_import_recommit(self):
        # No emails should have been generated.
        self.commitRevision('first')
        bzrsync = self.makeBzrSync(self.db_branch)
        bzrsync.syncBranchAndClose()
        stub.test_emails = []
        self.uncommitRevision()
        self.writeToFile(filename="hello.txt",
                         contents="Hello World\n")
        self.commitRevision('second')
        bzrsync = self.makeBzrSync(self.db_branch)
        bzrsync.syncBranchAndClose()
        self.assertNoPendingEmails()


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
