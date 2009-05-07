# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Unit tests for BranchView."""

__metaclass__ = type
__all__ = ['TestBranchView', 'test_suite']

from datetime import datetime, timedelta
from textwrap import dedent
import unittest

import pytz
import simplejson


from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.database.constants import UTC_NOW

from lp.code.browser.branch import (
    BranchAddView, BranchMirrorStatusView, BranchReviewerEditView,
    BranchSparkView, BranchView)
from lp.code.browser.branchlisting import PersonOwnedBranchesView
from canonical.launchpad.helpers import truncate_text
from lp.code.interfaces.branch import BranchLifecycleStatus, BranchType
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.product import IProductSet
from lp.code.interfaces.branchlookup import IBranchLookup
from canonical.launchpad.testing import (
    login, login_person, logout, ANONYMOUS, TestCaseWithFactory)
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import (
    DatabaseFunctionalLayer, LaunchpadFunctionalLayer)


class TestBranchMirrorHidden(TestCaseWithFactory):
    """Make sure that the appropriate mirror locations are hidden."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        config.push(
            "test", dedent("""\
                [codehosting]
                private_mirror_hosts: private.example.com
                """))

    def tearDown(self):
        config.pop("test")
        TestCaseWithFactory.tearDown(self)

    def testNormalBranch(self):
        # A branch from a normal location is fine.
        branch = self.factory.makeAnyBranch(
            branch_type=BranchType.MIRRORED,
            url="http://example.com/good/mirror")
        view = BranchView(branch, LaunchpadTestRequest())
        self.assertTrue(view.user is None)
        self.assertEqual(
            "http://example.com/good/mirror", view.mirror_location)

    def testHiddenBranchAsAnonymous(self):
        # A branch location with a defined private host is hidden from
        # anonymous browsers.
        branch = self.factory.makeAnyBranch(
            branch_type=BranchType.MIRRORED,
            url="http://private.example.com/bzr-mysql/mysql-5.0")
        view = BranchView(branch, LaunchpadTestRequest())
        self.assertTrue(view.user is None)
        self.assertEqual(
            "<private server>", view.mirror_location)

    def testHiddenBranchAsBranchOwner(self):
        # A branch location with a defined private host is visible to the
        # owner.
        owner = self.factory.makePerson(
            email="eric@example.com", password="test")
        branch = self.factory.makeAnyBranch(
            branch_type=BranchType.MIRRORED,
            owner=owner,
            url="http://private.example.com/bzr-mysql/mysql-5.0")
        # Now log in the owner.
        logout()
        login('eric@example.com')
        view = BranchView(branch, LaunchpadTestRequest())
        self.assertEqual(view.user, owner)
        self.assertEqual(
            "http://private.example.com/bzr-mysql/mysql-5.0",
            view.mirror_location)

    def testHiddenBranchAsOtherLoggedInUser(self):
        # A branch location with a defined private host is hidden from other
        # users.
        owner = self.factory.makePerson(
            email="eric@example.com", password="test")
        other = self.factory.makePerson(
            email="other@example.com", password="test")
        branch = self.factory.makeAnyBranch(
            branch_type=BranchType.MIRRORED,
            owner=owner,
            url="http://private.example.com/bzr-mysql/mysql-5.0")
        # Now log in the other person.
        logout()
        login('other@example.com')
        view = BranchView(branch, LaunchpadTestRequest())
        self.assertEqual(view.user, other)
        self.assertEqual(
            "<private server>", view.mirror_location)


class TestBranchView(unittest.TestCase):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login(ANONYMOUS)
        self.request = LaunchpadTestRequest()

    def tearDown(self):
        logout()

    def testMirrorStatusMessageIsTruncated(self):
        """mirror_status_message is truncated if the text is overly long."""
        branch = getUtility(IBranchLookup).get(28)
        branch_view = BranchMirrorStatusView(branch, self.request)
        self.assertEqual(
            truncate_text(branch.mirror_status_message,
                          branch_view.MAXIMUM_STATUS_MESSAGE_LENGTH) + ' ...',
            branch_view.mirror_status_message)

    def testMirrorStatusMessage(self):
        """mirror_status_message on the view is the same as on the branch."""
        branch = getUtility(IBranchLookup).get(5)
        branch.mirrorFailed("This is a short error message.")
        branch_view = BranchMirrorStatusView(branch, self.request)
        self.assertTrue(
            len(branch.mirror_status_message)
            <= branch_view.MAXIMUM_STATUS_MESSAGE_LENGTH,
            "branch.mirror_status_message longer than expected: %r"
            % (branch.mirror_status_message,))
        self.assertEqual(
            branch.mirror_status_message, branch_view.mirror_status_message)
        self.assertEqual(
            "This is a short error message.",
            branch_view.mirror_status_message)

    def testBranchAddRequestsMirror(self):
        """Registering a mirrored branch requests a mirror."""
        arbitrary_person = getUtility(IPersonSet).get(1)
        arbitrary_product = getUtility(IProductSet).get(1)
        login(arbitrary_person.preferredemail.email)
        try:
            add_view = BranchAddView(arbitrary_person, self.request)
            add_view.initialize()
            data = {
                'branch_type': BranchType.MIRRORED,
                'name': 'some-branch',
                'url': 'http://example.com',
                'title': 'Branch Title',
                'summary': '',
                'lifecycle_status': BranchLifecycleStatus.DEVELOPMENT,
                'whiteboard': '',
                'owner': arbitrary_person,
                'author': arbitrary_person,
                'product': arbitrary_product
                }
            add_view.add_action.success(data)
            # Make sure that next_mirror_time is a datetime, not an sqlbuilder
            # expression.
            removeSecurityProxy(add_view.branch).sync()
            now = datetime.now(pytz.timezone('UTC'))
            self.assertNotEqual(None, add_view.branch.next_mirror_time)
            self.assertTrue(
                add_view.branch.next_mirror_time < now,
                "next_mirror_time not set to UTC_NOW: %s < %s"
                % (add_view.branch.next_mirror_time, now))
        finally:
            logout()


class TestBranchReviewerEditView(TestCaseWithFactory):
    """Test the BranchReviewerEditView view."""

    layer = DatabaseFunctionalLayer

    def test_initial_reviewer_not_set(self):
        # If the reviewer is not set, the field is populated with the owner of
        # the branch.
        branch = self.factory.makeAnyBranch()
        self.assertIs(None, branch.reviewer)
        view = BranchReviewerEditView(branch, LaunchpadTestRequest())
        self.assertEqual(
            branch.owner,
            view.initial_values['reviewer'])

    def test_initial_reviewer_set(self):
        # If the reviewer has been set, it is shown as the initial value.
        branch = self.factory.makeAnyBranch()
        login_person(branch.owner)
        branch.reviewer = self.factory.makePerson()
        view = BranchReviewerEditView(branch, LaunchpadTestRequest())
        self.assertEqual(
            branch.reviewer,
            view.initial_values['reviewer'])

    def test_set_reviewer(self):
        # Test setting the reviewer.
        branch = self.factory.makeAnyBranch()
        reviewer = self.factory.makePerson()
        login_person(branch.owner)
        view = BranchReviewerEditView(branch, LaunchpadTestRequest())
        view.save_action.success({'reviewer': reviewer})
        self.assertEqual(reviewer, branch.reviewer)
        # Last modified has been updated.
        self.assertSqlAttributeEqualsDate(
            branch, 'date_last_modified', UTC_NOW)

    def test_set_reviewer_as_owner_clears_reviewer(self):
        # If the reviewer is set to be the branch owner, the review field is
        # cleared in the database.
        branch = self.factory.makeAnyBranch()
        login_person(branch.owner)
        branch.reviewer = self.factory.makePerson()
        view = BranchReviewerEditView(branch, LaunchpadTestRequest())
        view.save_action.success({'reviewer': branch.owner})
        self.assertIs(None, branch.reviewer)
        # Last modified has been updated.
        self.assertSqlAttributeEqualsDate(
            branch, 'date_last_modified', UTC_NOW)

    def test_set_reviewer_to_same_does_not_update_last_modified(self):
        # If the user has set the reviewer to be same and clicked on save,
        # then the underlying object hasn't really been changed, so the last
        # modified is not updated.
        modified_date = datetime(2007, 1, 1, tzinfo=pytz.UTC)
        branch = self.factory.makeAnyBranch(date_created=modified_date)
        view = BranchReviewerEditView(branch, LaunchpadTestRequest())
        view.save_action.success({'reviewer': branch.owner})
        self.assertIs(None, branch.reviewer)
        # Last modified has not been updated.
        self.assertEqual(modified_date, branch.date_last_modified)


class TestBranchBzrIdentity(TestCaseWithFactory):
    """Test the bzr_identity on the PersonOwnedBranchesView."""

    layer = DatabaseFunctionalLayer

    def test_dev_focus_identity(self):
        # A branch that is a development focus branch, should show using the
        # short name on the listing.
        product = self.factory.makeProduct(name="fooix")
        branch = self.factory.makeProductBranch(product=product)
        # To avoid dealing with admins, just log in the product owner to set
        # the development focus branch.
        login_person(product.owner)
        product.development_focus.branch = branch
        view = PersonOwnedBranchesView(branch.owner, LaunchpadTestRequest())
        view.initialize()
        navigator = view.branches()
        [decorated_branch] = navigator.branches()
        self.assertEqual("lp://dev/fooix", decorated_branch.bzr_identity)


class TestBranchSparkView(TestCaseWithFactory):
    """Tests for the BranchSparkView class."""

    layer = DatabaseFunctionalLayer

    def test_empty_branch(self):
        # A branch with no commits produces...
        branch = self.factory.makeAnyBranch()
        view = BranchSparkView(branch, LaunchpadTestRequest())
        json = simplejson.loads(view.render())
        self.assertEqual(0, json['count'])
        self.assertEqual('empty branch', json['last_commit'])

    def test_old_commits(self):
        # A branch with a commit older than the COMMIT_DAYS will create a list
        # of commits that all say zero.
        branch = self.factory.makeAnyBranch()
        revision = self.factory.makeRevision(
            revision_date=datetime(
                year=2008, month=9, day=10, tzinfo=pytz.UTC))
        branch.createBranchRevision(1, revision)
        branch.updateScannedDetails(revision, 1)

        view = BranchSparkView(branch, LaunchpadTestRequest())
        json = simplejson.loads(view.render())

        self.assertEqual(0, json['count'])
        self.assertEqual([0] * 90, json['commits'])
        self.assertEqual('2008-09-10', json['last_commit'])

    def test_last_commit_string(self):
        # If the last commit was very recent, we get a nicer string.
        branch = self.factory.makeAnyBranch()
        # Make the revision date six hours ago.
        revision_date = datetime.now(tz=pytz.UTC) - timedelta(seconds=6*3600)
        revision = self.factory.makeRevision(
            revision_date=revision_date)
        branch.createBranchRevision(1, revision)
        branch.updateScannedDetails(revision, 1)

        view = BranchSparkView(branch, LaunchpadTestRequest())
        json = simplejson.loads(view.render())
        self.assertEqual('6 hours ago', json['last_commit'])

    def test_new_commits(self):
        # If there are no commits for the day, there are zeros, if there are
        # commits, then the array contains the number of commits for that day.
        branch = self.factory.makeAnyBranch()
        # Create a commit 5 days ago.
        revision_date = datetime.now(tz=pytz.UTC) - timedelta(days=5)
        revision = self.factory.makeRevision(revision_date=revision_date)
        branch.createBranchRevision(1, revision)
        branch.updateScannedDetails(revision, 1)

        view = BranchSparkView(branch, LaunchpadTestRequest())
        json = simplejson.loads(view.render())

        self.assertEqual(1, json['count'])
        commits = ([0] * 84) + [1, 0, 0, 0, 0, 0]
        self.assertEqual(commits, json['commits'])
        self.assertEqual(84, json['max_commits'])

    def test_commit_for_just_now(self):
        # A commit now should show as a commit on the last day.
        branch = self.factory.makeAnyBranch()
        revision_date = datetime.now(tz=pytz.UTC)
        revision = self.factory.makeRevision(revision_date=revision_date)
        branch.createBranchRevision(1, revision)
        branch.updateScannedDetails(revision, 1)

        view = BranchSparkView(branch, LaunchpadTestRequest())
        json = simplejson.loads(view.render())

        self.assertEqual(1, json['count'])
        commits = ([0] * 89) + [1]
        self.assertEqual(commits, json['commits'])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
