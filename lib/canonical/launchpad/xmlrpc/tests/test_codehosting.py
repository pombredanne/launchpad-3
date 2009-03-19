# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the internal codehosting API."""

__metaclass__ = type

import datetime
import pytz
import unittest

from bzrlib.urlutils import escape

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.codehosting.inmemory import InMemoryFrontend
from canonical.database.constants import UTC_NOW
from canonical.launchpad.ftests import ANONYMOUS, login, logout
from canonical.launchpad.interfaces.launchpad import ILaunchBag
from canonical.launchpad.interfaces.branch import (
    BranchType, BRANCH_NAME_VALIDATION_ERROR_MESSAGE)
from canonical.launchpad.interfaces.branchlookup import IBranchLookup
from canonical.launchpad.interfaces.scriptactivity import (
    IScriptActivitySet)
from canonical.launchpad.interfaces.codehosting import (
    BRANCH_TRANSPORT, CONTROL_TRANSPORT)
from canonical.launchpad.testing import (
    LaunchpadObjectFactory, TestCase, TestCaseWithFactory)
from canonical.launchpad.webapp.interfaces import NotFoundError
from canonical.launchpad.xmlrpc.codehosting import (
    BranchFileSystem, BranchPuller, LAUNCHPAD_ANONYMOUS, LAUNCHPAD_SERVICES,
    iter_split, run_with_login)
from canonical.launchpad.xmlrpc import faults
from canonical.testing import DatabaseFunctionalLayer, FunctionalLayer


UTC = pytz.timezone('UTC')


def get_logged_in_username(requester=None):
    """Return the username of the logged in person.

    Used by `TestRunWithLogin`.
    """
    user = getUtility(ILaunchBag).user
    if user is None:
        return None
    return user.name


class TestRunWithLogin(TestCaseWithFactory):
    """Tests for the `run_with_login` decorator."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestRunWithLogin, self).setUp()
        self.person = self.factory.makePerson()

    def test_loginAsRequester(self):
        # run_with_login logs in as user given as the first argument
        # to the method being decorated.
        username = run_with_login(self.person.id, get_logged_in_username)
        # person.name is a protected field so we must be logged in before
        # attempting to access it.
        login(ANONYMOUS)
        self.assertEqual(self.person.name, username)
        logout()

    def test_loginAsRequesterName(self):
        # run_with_login can take a username as well as user id.
        username = run_with_login(self.person.name, get_logged_in_username)
        login(ANONYMOUS)
        self.assertEqual(self.person.name, username)
        logout()

    def test_logoutAtEnd(self):
        # run_with_login logs out once the decorated method is
        # finished.
        run_with_login(self.person.id, get_logged_in_username)
        self.assertEqual(None, get_logged_in_username())

    def test_logoutAfterException(self):
        # run_with_login logs out even if the decorated method raises
        # an exception.
        def raise_exception(requester, exc_factory, *args):
            raise exc_factory(*args)
        self.assertRaises(
            RuntimeError, run_with_login, self.person.id, raise_exception,
            RuntimeError, 'error message')
        self.assertEqual(None, get_logged_in_username())

    def test_passesRequesterInAsPerson(self):
        # run_with_login passes in the Launchpad Person object of the
        # requesting user.
        user = run_with_login(self.person.id, lambda x: x)
        login(ANONYMOUS)
        self.assertEqual(self.person.name, user.name)
        logout()

    def test_invalidRequester(self):
        # A method wrapped with run_with_login raises NotFoundError if
        # there is no person with the passed in id.
        self.assertRaises(
            NotFoundError, run_with_login, -1, lambda x: None)

    def test_cheatsForLaunchpadServices(self):
        # Various Launchpad services need to use the authserver to get
        # information about branches, unencumbered by petty
        # restrictions of ownership or privacy. `run_with_login`
        # detects the special username `LAUNCHPAD_SERVICES` and passes
        # that through to the decorated function without logging in.
        username = run_with_login(LAUNCHPAD_SERVICES, lambda x: x)
        self.assertEqual(LAUNCHPAD_SERVICES, username)
        login_id = run_with_login(LAUNCHPAD_SERVICES, get_logged_in_username)
        self.assertEqual(None, login_id)


class BranchPullerTest(TestCaseWithFactory):
    """Tests for the implementation of `IBranchPuller`.

    :ivar frontend: A nullary callable that returns an object that implements
        getPullerEndpoint, getLaunchpadObjectFactory and getBranchLookup.
    """

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        frontend = self.frontend()
        self.storage = frontend.getPullerEndpoint()
        self.factory = frontend.getLaunchpadObjectFactory()
        self.branch_lookup = frontend.getBranchLookup()
        self.getLastActivity = frontend.getLastActivity

    def assertFaultEqual(self, expected_fault, observed_fault):
        """Assert that `expected_fault` equals `observed_fault`."""
        self.assertIsInstance(observed_fault, faults.LaunchpadFault)
        self.assertEqual(expected_fault.faultCode, observed_fault.faultCode)
        self.assertEqual(
            expected_fault.faultString, observed_fault.faultString)

    def assertMirrorFailed(self, branch, failure_message, num_failures=1):
        """Assert that `branch` failed to mirror.

        :param branch: The branch that failed to mirror.
        :param failure_message: The last message that the branch failed with.
        :param num_failures: The number of times this branch has failed to
            mirror. Defaults to one.
        """
        self.assertSqlAttributeEqualsDate(
            branch, 'last_mirror_attempt', UTC_NOW)
        self.assertIs(None, branch.last_mirrored)
        self.assertEqual(num_failures, branch.mirror_failures)
        self.assertEqual(failure_message, branch.mirror_status_message)

    def assertMirrorSucceeded(self, branch, revision_id):
        """Assert that `branch` mirrored to `revision_id`."""
        self.assertSqlAttributeEqualsDate(
            branch, 'last_mirror_attempt', UTC_NOW)
        self.assertSqlAttributeEqualsDate(
            branch, 'last_mirrored', UTC_NOW)
        self.assertEqual(0, branch.mirror_failures)
        self.assertEqual(revision_id, branch.last_mirrored_id)

    def assertUnmirrored(self, branch):
        """Assert that `branch` has not yet been mirrored.

        Asserts that last_mirror_attempt, last_mirrored and
        mirror_status_message are all None, and that mirror_failures is 0.
        """
        self.assertIs(None, branch.last_mirror_attempt)
        self.assertIs(None, branch.last_mirrored)
        self.assertEqual(0, branch.mirror_failures)
        self.assertIs(None, branch.mirror_status_message)

    def getUnusedBranchID(self):
        """Return a branch ID that isn't in the database."""
        branch_id = 999
        # We can't be sure until the sample data is gone.
        self.assertIs(self.branch_lookup.get(branch_id), None)
        return branch_id

    def test_startMirroring(self):
        # startMirroring updates last_mirror_attempt to 'now', leaves
        # last_mirrored alone and returns True when passed the id of an
        # existing branch.
        branch = self.factory.makeAnyBranch()
        self.assertUnmirrored(branch)

        success = self.storage.startMirroring(branch.id)
        self.assertEqual(success, True)

        self.assertSqlAttributeEqualsDate(
            branch, 'last_mirror_attempt', UTC_NOW)
        self.assertIs(None, branch.last_mirrored)

    def test_startMirroringInvalidBranch(self):
        # startMirroring returns False when given a branch id which does not
        # exist.
        invalid_id = self.getUnusedBranchID()
        fault = self.storage.startMirroring(invalid_id)
        self.assertFaultEqual(faults.NoBranchWithID(invalid_id), fault)

    def test_mirrorFailed(self):
        branch = self.factory.makeAnyBranch()
        self.assertUnmirrored(branch)

        self.storage.startMirroring(branch.id)
        failure_message = self.factory.getUniqueString()
        success = self.storage.mirrorFailed(branch.id, failure_message)
        self.assertEqual(True, success)
        self.assertMirrorFailed(branch, failure_message)

    def test_mirrorFailedWithNotBranchID(self):
        branch_id = self.getUnusedBranchID()
        failure_message = self.factory.getUniqueString()
        fault = self.storage.mirrorFailed(branch_id, failure_message)
        self.assertFaultEqual(faults.NoBranchWithID(branch_id), fault)

    def test_mirrorComplete(self):
        # mirrorComplete marks the branch as having been successfully
        # mirrored, with no failures and no status message.
        branch = self.factory.makeAnyBranch()
        self.assertUnmirrored(branch)

        self.storage.startMirroring(branch.id)
        revision_id = self.factory.getUniqueString()
        success = self.storage.mirrorComplete(branch.id, revision_id)
        self.assertEqual(True, success)
        self.assertMirrorSucceeded(branch, revision_id)

    def test_mirrorCompleteWithNoBranchID(self):
        # mirrorComplete returns a Fault if there's no branch with the given
        # ID.
        branch_id = self.getUnusedBranchID()
        fault = self.storage.mirrorComplete(
            branch_id, self.factory.getUniqueString())
        self.assertFaultEqual(faults.NoBranchWithID(branch_id), fault)

    def test_mirrorComplete_resets_failure_count(self):
        # mirrorComplete marks the branch as successfully mirrored and removes
        # all memory of failure.

        # First, mark the branch as failed.
        branch = self.factory.makeAnyBranch()
        self.storage.startMirroring(branch.id)
        failure_message = self.factory.getUniqueString()
        self.storage.mirrorFailed(branch.id, failure_message)
        self.assertMirrorFailed(branch, failure_message)

        # Start and successfully finish a mirror.
        self.storage.startMirroring(branch.id)
        revision_id = self.factory.getUniqueString()
        self.storage.mirrorComplete(branch.id, revision_id)

        # Confirm that it succeeded.
        self.assertMirrorSucceeded(branch, revision_id)

    def test_mirrorComplete_resets_mirror_request(self):
        # After successfully mirroring a hosted branch, next_mirror_time
        # should be set to NULL.
        branch = self.factory.makeAnyBranch(branch_type=BranchType.HOSTED)

        # Request that branch be mirrored. This sets next_mirror_time.
        branch.requestMirror()

        # Simulate successfully mirroring the branch.
        self.storage.startMirroring(branch.id)
        self.storage.mirrorComplete(branch.id, self.factory.getUniqueString())

        self.assertIs(None, branch.next_mirror_time)

    def test_mirrorComplete_requests_mirror_for_incomplete_stacked(self):
        # After successfully mirroring a branch on which others are stacked,
        # any stacked branches with incomplete mirrors should have a mirror
        # requested. This prevents them from being trapped in a failed state.
        # See bug 261334.
        branch = self.factory.makeAnyBranch()
        stacked_branch = self.factory.makeAnyBranch(stacked_on=branch)

        # Note that no mirror is requested.
        self.assertIs(None, stacked_branch.next_mirror_time)

        self.storage.startMirroring(stacked_branch.id)
        self.storage.startMirroring(branch.id)
        self.storage.mirrorComplete(branch.id, self.factory.getUniqueString())
        self.assertSqlAttributeEqualsDate(
            stacked_branch, 'next_mirror_time', UTC_NOW)

    def test_mirrorCompleteRequestsMirrorForIncompleteStackedOnPrivate(self):
        # After successfully mirroring a *private* branch on which others are
        # stacked, any stacked branches with incomplete mirrors have a mirror
        # requested. See bug 261334.
        branch = removeSecurityProxy(
            self.factory.makeAnyBranch(private=True))
        stacked_branch = removeSecurityProxy(
            self.factory.makeAnyBranch(stacked_on=branch, private=True))

        # Note that no mirror is requested.
        self.assertIs(None, stacked_branch.next_mirror_time)

        self.storage.startMirroring(stacked_branch.id)
        self.storage.startMirroring(branch.id)
        self.storage.mirrorComplete(branch.id, self.factory.getUniqueString())
        self.assertSqlAttributeEqualsDate(
            stacked_branch, 'next_mirror_time', UTC_NOW)

    def test_mirrorCompletePrivateStackedOnPublic(self):
        # After successfully mirroring a *public* branch on which *private*
        # branche are stacked, any stacked branches with incomplete mirrors
        # have a mirror requested. See bug 261334.
        branch = self.factory.makeAnyBranch()
        stacked_branch = removeSecurityProxy(
            self.factory.makeAnyBranch(stacked_on=branch, private=True))

        # Note that no mirror is requested.
        self.assertIs(None, stacked_branch.next_mirror_time)

        self.storage.startMirroring(stacked_branch.id)
        self.storage.startMirroring(branch.id)
        self.storage.mirrorComplete(branch.id, self.factory.getUniqueString())
        self.assertSqlAttributeEqualsDate(
            stacked_branch, 'next_mirror_time', UTC_NOW)

    def test_recordSuccess(self):
        # recordSuccess must insert the given data into ScriptActivity.
        started = datetime.datetime(2007, 07, 05, 19, 32, 1, tzinfo=UTC)
        completed = datetime.datetime(2007, 07, 05, 19, 34, 24, tzinfo=UTC)
        started_tuple = tuple(started.utctimetuple())
        completed_tuple = tuple(completed.utctimetuple())
        success = self.storage.recordSuccess(
            'test-recordsuccess', 'vostok', started_tuple, completed_tuple)
        self.assertEqual(True, success)

        activity = self.getLastActivity('test-recordsuccess')
        self.assertEqual('vostok', activity.hostname)
        self.assertEqual(started, activity.date_started)
        self.assertEqual(completed, activity.date_completed)

    def test_setStackedOnDefaultURLFragment(self):
        # setStackedOn records that one branch is stacked on another. One way
        # to find the stacked-on branch is by the URL fragment that's
        # generated as part of Launchpad's default stacking.
        stacked_branch = self.factory.makeAnyBranch()
        stacked_on_branch = self.factory.makeAnyBranch()
        self.storage.setStackedOn(
            stacked_branch.id, '/%s' % stacked_on_branch.unique_name)
        self.assertEqual(stacked_branch.stacked_on, stacked_on_branch)

    def test_setStackedOnExternalURL(self):
        # If setStackedOn is passed an external URL, rather than a URL
        # fragment, it will mark the branch as being stacked on the branch in
        # Launchpad registered with that external URL.
        stacked_branch = self.factory.makeAnyBranch()
        stacked_on_branch = self.factory.makeAnyBranch(
            branch_type=BranchType.MIRRORED)
        self.storage.setStackedOn(stacked_branch.id, stacked_on_branch.url)
        self.assertEqual(stacked_branch.stacked_on, stacked_on_branch)

    def test_setStackedOnExternalURLWithTrailingSlash(self):
        # If setStackedOn is passed an external URL with a trailing slash, it
        # won't make a big deal out of it, it will treat it like any other
        # URL.
        stacked_branch = self.factory.makeAnyBranch()
        stacked_on_branch = self.factory.makeAnyBranch(
            branch_type=BranchType.MIRRORED)
        url = stacked_on_branch.url + '/'
        self.storage.setStackedOn(stacked_branch.id, url)
        self.assertEqual(stacked_branch.stacked_on, stacked_on_branch)

    def test_setStackedOnNothing(self):
        # If setStackedOn is passed an empty string as a stacked-on location,
        # the branch is marked as not being stacked on any branch.
        stacked_on_branch = self.factory.makeAnyBranch()
        stacked_branch = self.factory.makeAnyBranch(
            stacked_on=stacked_on_branch)
        self.storage.setStackedOn(stacked_branch.id, '')
        self.assertIs(stacked_branch.stacked_on, None)

    def test_setStackedOnBranchNotFound(self):
        # If setStackedOn can't find a branch for the given location, it will
        # return a Fault.
        stacked_branch = self.factory.makeAnyBranch()
        url = self.factory.getUniqueURL()
        fault = self.storage.setStackedOn(stacked_branch.id, url)
        self.assertFaultEqual(faults.NoSuchBranch(url), fault)

    def test_setStackedOnNoBranchWithID(self):
        # If setStackedOn is called for a branch that doesn't exist, it will
        # return a Fault.
        stacked_on_branch = self.factory.makeAnyBranch(
            branch_type=BranchType.MIRRORED)
        branch_id = self.getUnusedBranchID()
        fault = self.storage.setStackedOn(branch_id, stacked_on_branch.url)
        self.assertFaultEqual(faults.NoBranchWithID(branch_id), fault)


class BranchPullQueueTest(TestCaseWithFactory):
    """Tests for the pull queue methods of `IBranchPuller`."""

    def setUp(self):
        super(BranchPullQueueTest, self).setUp()
        frontend = self.frontend()
        self.storage = frontend.getPullerEndpoint()
        self.factory = frontend.getLaunchpadObjectFactory()

    def assertBranchQueues(self, hosted, mirrored, imported):
        expected_hosted = [
            self.storage._getBranchPullInfo(branch) for branch in hosted]
        expected_mirrored = [
            self.storage._getBranchPullInfo(branch) for branch in mirrored]
        expected_imported = [
            self.storage._getBranchPullInfo(branch) for branch in imported]
        self.assertEqual(
            expected_hosted, self.storage.getBranchPullQueue('HOSTED'))
        self.assertEqual(
            expected_mirrored, self.storage.getBranchPullQueue('MIRRORED'))
        self.assertEqual(
            expected_imported, self.storage.getBranchPullQueue('IMPORTED'))

    def test_pullQueuesEmpty(self):
        """getBranchPullQueue returns an empty list when there are no branches
        to pull.
        """
        self.assertBranchQueues([], [], [])

    def makeBranchAndRequestMirror(self, branch_type):
        """Make a branch of the given type and call requestMirror on it."""
        branch = self.factory.makeAnyBranch(branch_type=branch_type)
        branch.requestMirror()
        # The pull queues contain branches that have next_mirror_time strictly
        # in the past, but requestMirror sets this field to UTC_NOW, so we
        # push the time back slightly here to get the branch to show up in the
        # queue.
        naked_branch = removeSecurityProxy(branch)
        naked_branch.next_mirror_time -= datetime.timedelta(seconds=1)
        return branch

    def test_getBranchPullInfo_no_default_stacked_branch(self):
        # If there's no default stacked branch for the project that a branch
        # is on, then _getBranchPullInfo returns (id, url, unique_name, '').
        branch = self.factory.makeAnyBranch()
        info = self.storage._getBranchPullInfo(branch)
        self.assertEqual(
            (branch.id, branch.getPullURL(), branch.unique_name, ''), info)

    def test_getBranchPullInfo_default_stacked_branch(self):
        # If there's a default stacked branch for the project that a branch is
        # on, then _getBranchPullInfo returns (id, url, unique_name,
        # default_branch_unique_name).
        product = self.factory.makeProduct()
        default_branch = self.factory.enableDefaultStackingForProduct(product)
        branch = self.factory.makeProductBranch(product=product)
        info = self.storage._getBranchPullInfo(branch)
        self.assertEqual(
            (branch.id, branch.getPullURL(), branch.unique_name,
             '/' + default_branch.unique_name), info)

    def test_getBranchPullInfo_private_branch(self):
        # We don't want to stack mirrored branches onto private branches:
        # mirrored branches are public by their nature. This, if the default
        # stacked-on branch for the project is private and the branch is
        # MIRRORED then we don't include the default stacked-on branch's
        # details in the tuple.
        default_branch = self.factory.makeAnyBranch(private=True)
        product = removeSecurityProxy(default_branch).product
        product.development_focus.user_branch = default_branch
        mirrored_branch = self.factory.makeProductBranch(
            branch_type=BranchType.MIRRORED, product=product)
        info = self.storage._getBranchPullInfo(mirrored_branch)
        self.assertEqual(
            (mirrored_branch.id, mirrored_branch.getPullURL(),
             mirrored_branch.unique_name, ''), info)

    def test_getBranchPullInfo_junk(self):
        # _getBranchPullInfo returns (id, url, unique_name, '') for junk
        # branches.
        branch = self.factory.makePersonalBranch()
        info = self.storage._getBranchPullInfo(branch)
        self.assertEqual(
            (branch.id, branch.getPullURL(), branch.unique_name, ''), info)

    def test_requestMirrorPutsBranchInQueue_hosted(self):
        branch = self.makeBranchAndRequestMirror(BranchType.HOSTED)
        self.assertBranchQueues([branch], [], [])

    def test_requestMirrorPutsBranchInQueue_mirrored(self):
        branch = self.makeBranchAndRequestMirror(BranchType.MIRRORED)
        self.assertBranchQueues([], [branch], [])

    def test_requestMirrorPutsBranchInQueue_imported(self):
        branch = self.makeBranchAndRequestMirror(BranchType.IMPORTED)
        self.assertBranchQueues([], [], [branch])


class BranchFileSystemTest(TestCaseWithFactory):
    """Tests for the implementation of `IBranchFileSystem`."""

    def setUp(self):
        super(BranchFileSystemTest, self).setUp()
        frontend = self.frontend()
        self.branchfs = frontend.getFilesystemEndpoint()
        self.factory = frontend.getLaunchpadObjectFactory()
        self.branch_lookup = frontend.getBranchLookup()

    def assertFaultEqual(self, expected_fault, observed_fault):
        """Assert that `expected_fault` equals `observed_fault`."""
        self.assertIsInstance(observed_fault, faults.LaunchpadFault)
        self.assertEqual(expected_fault.faultCode, observed_fault.faultCode)
        self.assertEqual(
            expected_fault.faultString, observed_fault.faultString)

    def test_createBranch(self):
        # createBranch creates a branch with the supplied details and the
        # caller as registrant.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct()
        name = self.factory.getUniqueString()
        branch_id = self.branchfs.createBranch(
            owner.id, escape('/~%s/%s/%s' % (owner.name, product.name, name)))
        login(ANONYMOUS)
        branch = self.branch_lookup.get(branch_id)
        self.assertEqual(owner, branch.owner)
        self.assertEqual(product, branch.product)
        self.assertEqual(name, branch.name)
        self.assertEqual(owner, branch.registrant)
        self.assertEqual(BranchType.HOSTED, branch.branch_type)

    def test_createBranch_no_preceding_slash(self):
        requester = self.factory.makePerson()
        path = escape(u'invalid')
        fault = self.branchfs.createBranch(requester.id, path)
        login(ANONYMOUS)
        self.assertFaultEqual(faults.InvalidPath(path), fault)

    def test_createBranch_junk(self):
        # createBranch can create +junk branches.
        owner = self.factory.makePerson()
        name = self.factory.getUniqueString()
        branch_id = self.branchfs.createBranch(
            owner.id, escape('/~%s/%s/%s' % (owner.name, '+junk', name)))
        login(ANONYMOUS)
        branch = self.branch_lookup.get(branch_id)
        self.assertEqual(owner, branch.owner)
        self.assertEqual(None, branch.product)
        self.assertEqual(name, branch.name)
        self.assertEqual(owner, branch.registrant)
        self.assertEqual(BranchType.HOSTED, branch.branch_type)

    def test_createBranch_team_junk(self):
        # createBranch can create +junk branches on teams.
        registrant = self.factory.makePerson()
        team = self.factory.makeTeam(registrant)
        name = self.factory.getUniqueString()
        branch_id = self.branchfs.createBranch(
            registrant.id, escape('/~%s/+junk/%s' % (team.name, name)))
        login(ANONYMOUS)
        branch = self.branch_lookup.get(branch_id)
        self.assertEqual(team, branch.owner)
        self.assertEqual(None, branch.product)
        self.assertEqual(name, branch.name)
        self.assertEqual(registrant, branch.registrant)
        self.assertEqual(BranchType.HOSTED, branch.branch_type)

    def test_createBranch_bad_product(self):
        # Creating a branch for a non-existant product fails.
        owner = self.factory.makePerson()
        name = self.factory.getUniqueString()
        message = "Project 'no-such-product' does not exist."
        fault = self.branchfs.createBranch(
            owner.id, escape('/~%s/no-such-product/%s' % (owner.name, name)))
        self.assertFaultEqual(faults.NotFound(message), fault)

    def test_createBranch_other_user(self):
        # Creating a branch under another user's directory fails.
        creator = self.factory.makePerson()
        other_person = self.factory.makePerson()
        product = self.factory.makeProduct()
        name = self.factory.getUniqueString()
        message = ("%s cannot create branches owned by %s"
                   % (creator.displayname, other_person.displayname))
        fault = self.branchfs.createBranch(
            creator.id,
            escape('/~%s/%s/%s' % (other_person.name, product.name, name)))
        self.assertFaultEqual(faults.PermissionDenied(message), fault)

    def test_createBranch_bad_name(self):
        # Creating a branch with an invalid name fails.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct()
        invalid_name = 'invalid name!'
        message = ("Invalid branch name %r. %s"
                   % (invalid_name, BRANCH_NAME_VALIDATION_ERROR_MESSAGE))
        fault = self.branchfs.createBranch(
            owner.id, escape(
                '/~%s/%s/%s' % (owner.name, product.name, invalid_name)))
        self.assertFaultEqual(faults.PermissionDenied(message), fault)

    def test_createBranch_bad_user(self):
        # Creating a branch under a non-existent user fails.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct()
        name = self.factory.getUniqueString()
        message = "User/team 'no-one' does not exist."
        fault = self.branchfs.createBranch(
            owner.id, escape('/~no-one/%s/%s' % (product.name, name)))
        self.assertFaultEqual(faults.NotFound(message), fault)

    def test_createBranch_bad_user_bad_product(self):
        # If both the user and the product are not found, then the missing
        # user "wins" the error reporting race (as the url reads
        # ~user/product/branch).
        owner = self.factory.makePerson()
        name = self.factory.getUniqueString()
        message = "User/team 'no-one' does not exist."
        fault = self.branchfs.createBranch(
            owner.id, escape('/~no-one/no-product/%s' % (name,)))
        self.assertFaultEqual(faults.NotFound(message), fault)

    def test_createBranch_not_branch(self):
        # Trying to create a branch at a path that's not valid for branches
        # raises a PermissionDenied fault.
        owner = self.factory.makePerson()
        path = escape('/~%s' % owner.name)
        fault = self.branchfs.createBranch(owner.id, path)
        message = "Cannot create branch at '%s'" % path
        self.assertFaultEqual(faults.PermissionDenied(message), fault)

    def test_createBranch_source_package(self):
        # createBranch can take the path to a source package branch and create
        # it with all the right attributes.
        owner = self.factory.makePerson()
        sourcepackage = self.factory.makeSourcePackage()
        branch_name = self.factory.getUniqueString()
        unique_name = '/~%s/%s/%s/%s/%s' % (
            owner.name,
            sourcepackage.distribution.name,
            sourcepackage.distroseries.name,
            sourcepackage.sourcepackagename.name,
            branch_name)
        branch_id = self.branchfs.createBranch(owner.id, escape(unique_name))
        login(ANONYMOUS)
        branch = self.branch_lookup.get(branch_id)
        self.assertEqual(owner, branch.owner)
        self.assertEqual(sourcepackage.distroseries, branch.distroseries)
        self.assertEqual(
            sourcepackage.sourcepackagename, branch.sourcepackagename)
        self.assertEqual(branch_name, branch.name)
        self.assertEqual(owner, branch.registrant)
        self.assertEqual(BranchType.HOSTED, branch.branch_type)

    def test_createBranch_invalid_distro(self):
        # If createBranch is called with the path to a non-existent distro, it
        # will return a Fault saying so in plain English.
        owner = self.factory.makePerson()
        distroseries = self.factory.makeDistroRelease()
        sourcepackagename = self.factory.makeSourcePackageName()
        branch_name = self.factory.getUniqueString()
        unique_name = '/~%s/ningnangnong/%s/%s/%s' % (
            owner.name, distroseries.name, sourcepackagename.name,
            branch_name)
        fault = self.branchfs.createBranch(owner.id, escape(unique_name))
        message = "No such distribution: 'ningnangnong'."
        self.assertFaultEqual(faults.NotFound(message), fault)

    def test_createBranch_invalid_distroseries(self):
        # If createBranch is called with the path to a non-existent
        # distroseries, it will return a Fault saying so.
        owner = self.factory.makePerson()
        distribution = self.factory.makeDistribution()
        sourcepackagename = self.factory.makeSourcePackageName()
        branch_name = self.factory.getUniqueString()
        unique_name = '/~%s/%s/ningnangnong/%s/%s' % (
            owner.name, distribution.name, sourcepackagename.name,
            branch_name)
        fault = self.branchfs.createBranch(owner.id, escape(unique_name))
        message = "No such distribution series: 'ningnangnong'."
        self.assertFaultEqual(faults.NotFound(message), fault)

    def test_createBranch_invalid_sourcepackagename(self):
        # If createBranch is called with the path to an invalid source
        # package, it will return a Fault saying so.
        owner = self.factory.makePerson()
        distroseries = self.factory.makeDistroRelease()
        branch_name = self.factory.getUniqueString()
        unique_name = '/~%s/%s/%s/ningnangnong/%s' % (
            owner.name, distroseries.distribution.name, distroseries.name,
            branch_name)
        fault = self.branchfs.createBranch(owner.id, escape(unique_name))
        message = "No such source package: 'ningnangnong'."
        self.assertFaultEqual(faults.NotFound(message), fault)

    def test_initialMirrorRequest(self):
        # The default 'next_mirror_time' for a newly created hosted branch
        # should be None.
        branch = self.factory.makeAnyBranch(branch_type=BranchType.HOSTED)
        self.assertIs(None, branch.next_mirror_time)

    def test_requestMirror(self):
        # requestMirror should set the next_mirror_time field to be the
        # current time.
        requester = self.factory.makePerson()
        branch = self.factory.makeAnyBranch(branch_type=BranchType.HOSTED)
        self.branchfs.requestMirror(requester.id, branch.id)
        self.assertSqlAttributeEqualsDate(
            branch, 'next_mirror_time', UTC_NOW)

    def test_requestMirror_private(self):
        # requestMirror can be used to request the mirror of a private branch.
        requester = self.factory.makePerson()
        branch = self.factory.makeAnyBranch(owner=requester, private=True)
        branch = removeSecurityProxy(branch)
        self.branchfs.requestMirror(requester.id, branch.id)
        self.assertSqlAttributeEqualsDate(
            branch, 'next_mirror_time', UTC_NOW)

    def assertCannotTranslate(self, requester, path):
        """Assert that we cannot translate 'path'."""
        fault = self.branchfs.translatePath(requester.id, path)
        self.assertFaultEqual(faults.PathTranslationError(path), fault)

    def assertNotFound(self, requester, path):
        """Assert that the given path cannot be found."""
        if requester not in [LAUNCHPAD_ANONYMOUS, LAUNCHPAD_SERVICES]:
            requester = requester.id
        fault = self.branchfs.translatePath(requester, path)
        self.assertFaultEqual(faults.PathTranslationError(path), fault)

    def assertPermissionDenied(self, requester, path):
        """Assert that looking at the given path gives permission denied."""
        if requester not in [LAUNCHPAD_ANONYMOUS, LAUNCHPAD_SERVICES]:
            requester = requester.id
        fault = self.branchfs.translatePath(requester, path)
        self.assertFaultEqual(faults.PermissionDenied(), fault)

    def _makeProductWithDevFocus(self, private=False):
        """Make a stacking-enabled product with a development focus.

        :param private: Whether the development focus branch should be
            private.
        :return: The new Product and the new Branch.
        """
        product = self.factory.makeProduct()
        branch = self.factory.makeProductBranch(private=private)
        self.factory.enableDefaultStackingForProduct(product, branch)
        self.assertEqual(product.default_stacked_on_branch, branch)
        return product, branch

    def test_translatePath_cannot_translate(self):
        # Sometimes translatePath will not know how to translate a path. When
        # this happens, it returns a Fault saying so, including the path it
        # couldn't translate.
        requester = self.factory.makePerson()
        path = escape(u'/untranslatable')
        self.assertCannotTranslate(requester, path)

    def test_translatePath_no_preceding_slash(self):
        requester = self.factory.makePerson()
        path = escape(u'invalid')
        fault = self.branchfs.translatePath(requester.id, path)
        self.assertFaultEqual(faults.InvalidPath(path), fault)

    def test_translatePath_branch(self):
        requester = self.factory.makePerson()
        branch = self.factory.makeAnyBranch()
        path = escape(u'/%s' % branch.unique_name)
        translation = self.branchfs.translatePath(requester.id, path)
        login(ANONYMOUS)
        self.assertEqual(
            (BRANCH_TRANSPORT, {'id': branch.id, 'writable': False}, ''),
            translation)

    def test_translatePath_branch_with_trailing_slash(self):
        requester = self.factory.makePerson()
        branch = self.factory.makeAnyBranch()
        path = escape(u'/%s/' % branch.unique_name)
        translation = self.branchfs.translatePath(requester.id, path)
        login(ANONYMOUS)
        self.assertEqual(
            (BRANCH_TRANSPORT, {'id': branch.id, 'writable': False}, ''),
            translation)

    def test_translatePath_path_in_branch(self):
        requester = self.factory.makePerson()
        branch = self.factory.makeAnyBranch()
        path = escape(u'/%s/child' % branch.unique_name)
        translation = self.branchfs.translatePath(requester.id, path)
        login(ANONYMOUS)
        self.assertEqual(
            (BRANCH_TRANSPORT, {'id': branch.id, 'writable': False}, 'child'),
            translation)

    def test_translatePath_nested_path_in_branch(self):
        requester = self.factory.makePerson()
        branch = self.factory.makeAnyBranch()
        path = escape(u'/%s/a/b' % branch.unique_name)
        translation = self.branchfs.translatePath(requester.id, path)
        login(ANONYMOUS)
        self.assertEqual(
            (BRANCH_TRANSPORT, {'id': branch.id, 'writable': False}, 'a/b'),
            translation)

    def test_translatePath_preserves_escaping(self):
        requester = self.factory.makePerson()
        branch = self.factory.makeAnyBranch()
        child_path = u'a@b'
        # This test is only meaningful if the path isn't the same when
        # escaped.
        self.assertNotEqual(escape(child_path), child_path.encode('utf-8'))
        path = escape(u'/%s/%s' % (branch.unique_name, child_path))
        translation = self.branchfs.translatePath(requester.id, path)
        login(ANONYMOUS)
        self.assertEqual(
            (BRANCH_TRANSPORT,
             {'id': branch.id, 'writable': False},
             escape(child_path)), translation)

    def test_translatePath_no_such_junk_branch(self):
        requester = self.factory.makePerson()
        path = '/~%s/+junk/.bzr/branch-format' % (requester.name,)
        self.assertNotFound(requester, path)

    def test_translatePath_branches_in_parent_dirs_not_found(self):
        requester = self.factory.makePerson()
        product = self.factory.makeProduct()
        path = '/~%s/%s/.bzr/branch-format' % (requester.name, product.name)
        self.assertNotFound(requester, path)

    def test_translatePath_no_such_branch(self):
        requester = self.factory.makePerson()
        product = self.factory.makeProduct()
        path = '/~%s/%s/no-such-branch' % (requester.name, product.name)
        self.assertNotFound(requester, path)

    def test_translatePath_private_branch(self):
        requester = self.factory.makePerson()
        branch = removeSecurityProxy(
            self.factory.makeAnyBranch(
                branch_type=BranchType.HOSTED, private=True, owner=requester))
        path = escape(u'/%s' % branch.unique_name)
        translation = self.branchfs.translatePath(requester.id, path)
        login(ANONYMOUS)
        self.assertEqual(
            (BRANCH_TRANSPORT, {'id': branch.id, 'writable': True}, ''),
            translation)

    def test_translatePath_cant_see_private_branch(self):
        requester = self.factory.makePerson()
        branch = removeSecurityProxy(self.factory.makeAnyBranch(private=True))
        path = escape(u'/%s' % branch.unique_name)
        self.assertPermissionDenied(requester, path)

    def test_translatePath_remote_branch(self):
        requester = self.factory.makePerson()
        branch = self.factory.makeAnyBranch(branch_type=BranchType.REMOTE)
        path = escape(u'/%s' % branch.unique_name)
        self.assertNotFound(requester, path)

    def test_translatePath_launchpad_services_private(self):
        branch = removeSecurityProxy(self.factory.makeAnyBranch(private=True))
        path = escape(u'/%s' % branch.unique_name)
        translation = self.branchfs.translatePath(LAUNCHPAD_SERVICES, path)
        login(ANONYMOUS)
        self.assertEqual(
            (BRANCH_TRANSPORT, {'id': branch.id, 'writable': False}, ''),
            translation)

    def test_translatePath_anonymous_cant_see_private_branch(self):
        branch = removeSecurityProxy(self.factory.makeAnyBranch(private=True))
        path = escape(u'/%s' % branch.unique_name)
        self.assertPermissionDenied(LAUNCHPAD_ANONYMOUS, path)

    def test_translatePath_anonymous_public_branch(self):
        branch = self.factory.makeAnyBranch()
        path = escape(u'/%s' % branch.unique_name)
        translation = self.branchfs.translatePath(LAUNCHPAD_ANONYMOUS, path)
        self.assertEqual(
            (BRANCH_TRANSPORT, {'id': branch.id, 'writable': False}, ''),
            translation)

    def test_translatePath_owned(self):
        requester = self.factory.makePerson()
        branch = self.factory.makeAnyBranch(
            branch_type=BranchType.HOSTED, owner=requester)
        path = escape(u'/%s' % branch.unique_name)
        translation = self.branchfs.translatePath(requester.id, path)
        login(ANONYMOUS)
        self.assertEqual(
            (BRANCH_TRANSPORT, {'id': branch.id, 'writable': True}, ''),
            translation)

    def test_translatePath_team_owned(self):
        requester = self.factory.makePerson()
        team = self.factory.makeTeam(requester)
        branch = self.factory.makeAnyBranch(
            branch_type=BranchType.HOSTED, owner=team)
        path = escape(u'/%s' % branch.unique_name)
        translation = self.branchfs.translatePath(requester.id, path)
        login(ANONYMOUS)
        self.assertEqual(
            (BRANCH_TRANSPORT, {'id': branch.id, 'writable': True}, ''),
            translation)

    def test_translatePath_team_unowned(self):
        requester = self.factory.makePerson()
        team = self.factory.makeTeam(self.factory.makePerson())
        branch = self.factory.makeAnyBranch(
            branch_type=BranchType.HOSTED, owner=team)
        path = escape(u'/%s' % branch.unique_name)
        translation = self.branchfs.translatePath(requester.id, path)
        login(ANONYMOUS)
        self.assertEqual(
            (BRANCH_TRANSPORT, {'id': branch.id, 'writable': False}, ''),
            translation)

    def test_translatePath_owned_mirrored(self):
        requester = self.factory.makePerson()
        branch = self.factory.makeAnyBranch(
            branch_type=BranchType.MIRRORED, owner=requester)
        path = escape(u'/%s' % branch.unique_name)
        translation = self.branchfs.translatePath(requester.id, path)
        login(ANONYMOUS)
        self.assertEqual(
            (BRANCH_TRANSPORT, {'id': branch.id, 'writable': False}, ''),
            translation)

    def test_translatePath_owned_imported(self):
        requester = self.factory.makePerson()
        branch = self.factory.makeAnyBranch(
            branch_type=BranchType.IMPORTED, owner=requester)
        path = escape(u'/%s' % branch.unique_name)
        translation = self.branchfs.translatePath(requester.id, path)
        login(ANONYMOUS)
        self.assertEqual(
            (BRANCH_TRANSPORT, {'id': branch.id, 'writable': False}, ''),
            translation)

    def assertControlDirectory(self, unique_name, trailing_path, translation):
        """Assert that 'translation' points to the right control transport."""
        unique_name = escape(u'/' + unique_name)
        expected_translation = (
            CONTROL_TRANSPORT,
            {'default_stack_on': unique_name}, trailing_path)
        self.assertEqual(expected_translation, translation)

    def test_translatePath_control_directory(self):
        requester = self.factory.makePerson()
        product, branch = self._makeProductWithDevFocus()
        path = escape(u'/~%s/%s/.bzr' % (requester.name, product.name))
        translation = self.branchfs.translatePath(requester.id, path)
        login(ANONYMOUS)
        self.assertControlDirectory(branch.unique_name, '.bzr/', translation)

    def test_translatePath_control_directory_no_stacked_set(self):
        # When there's no default stacked-on branch set for the project, we
        # don't even bother translating control directory paths.
        requester = self.factory.makePerson()
        product = self.factory.makeProduct()
        path = escape(u'/~%s/%s/.bzr/' % (requester.name, product.name))
        self.assertNotFound(requester, path)

    def test_translatePath_control_directory_invisble_branch(self):
        requester = self.factory.makePerson()
        product, branch = self._makeProductWithDevFocus(private=True)
        path = escape(u'/~%s/%s/.bzr/' % (requester.name, product.name))
        self.assertNotFound(requester, path)

    def test_translatePath_control_directory_private_branch(self):
        product, branch = self._makeProductWithDevFocus(private=True)
        branch = removeSecurityProxy(branch)
        requester = branch.owner
        path = escape(u'/~%s/%s/.bzr/' % (requester.name, product.name))
        translation = self.branchfs.translatePath(requester.id, path)
        login(ANONYMOUS)
        self.assertControlDirectory(branch.unique_name, '.bzr/', translation)

    def test_translatePath_control_directory_other_owner(self):
        requester = self.factory.makePerson()
        product, branch = self._makeProductWithDevFocus()
        owner = self.factory.makePerson()
        path = escape(u'/~%s/%s/.bzr' % (owner.name, product.name))
        translation = self.branchfs.translatePath(requester.id, path)
        login(ANONYMOUS)
        self.assertControlDirectory(branch.unique_name, '.bzr/', translation)


class TestIterateSplit(TestCase):
    """Tests for iter_split."""

    def test_iter_split(self):
        # iter_split loops over each way of splitting a string in two using
        # the given splitter.
        self.assertEqual([('one', '')], list(iter_split('one', '/')))
        self.assertEqual([], list(iter_split('', '/')))
        self.assertEqual(
            [('one/two', ''), ('one', 'two')],
            list(iter_split('one/two', '/')))
        self.assertEqual(
            [('one/two/three', ''), ('one/two', 'three'),
             ('one', 'two/three')],
            list(iter_split('one/two/three', '/')))


class LaunchpadDatabaseFrontend:
    """A 'frontend' to Launchpad's branch services.

    A 'frontend' here means something that provides access to the various
    XML-RPC endpoints, object factories and 'database' methods needed to write
    unit tests for XML-RPC endpoints.

    All of these methods are gathered together in this class so that
    alternative implementations can be provided, see `InMemoryFrontend`.
    """

    def getFilesystemEndpoint(self):
        """Return the branch filesystem endpoint for testing."""
        return BranchFileSystem(None, None)

    def getPullerEndpoint(self):
        """Return the branch puller endpoint for testing."""
        return BranchPuller(None, None)

    def getLaunchpadObjectFactory(self):
        """Return the Launchpad object factory for testing.

        See `LaunchpadObjectFactory`.
        """
        return LaunchpadObjectFactory()

    def getBranchLookup(self):
        """Return an implementation of `IBranchLookup`.

        Tests should use this to get the branch set they need, rather than
        using 'getUtility(IBranchSet)'. This allows in-memory implementations
        to work correctly.
        """
        return getUtility(IBranchLookup)

    def getLastActivity(self, activity_name):
        """Get the last script activity with 'activity_name'."""
        return getUtility(IScriptActivitySet).getLastActivity(activity_name)


def test_suite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    puller_tests = unittest.TestSuite(
        [loader.loadTestsFromTestCase(BranchPullerTest),
         loader.loadTestsFromTestCase(BranchPullQueueTest),
         loader.loadTestsFromTestCase(BranchFileSystemTest),
         ])
    scenarios = [
        ('db', {'frontend': LaunchpadDatabaseFrontend,
                'layer': DatabaseFunctionalLayer}),
        ('inmemory', {'frontend': InMemoryFrontend,
                      'layer': FunctionalLayer}),
        ]
    try:
        from bzrlib.tests import multiply_tests
        multiply_tests(puller_tests, scenarios, suite)
    except ImportError:
        # XXX: MichaelHudson, 2009-03-11: This except clause can be deleted
        # once sourcecode/bzr has bzr.dev r4102.
        from bzrlib.tests import adapt_tests, TestScenarioApplier
        applier = TestScenarioApplier()
        applier.scenarios = scenarios
        adapt_tests(puller_tests, applier, suite)
    suite.addTests(
        map(loader.loadTestsFromTestCase,
            [TestRunWithLogin, TestIterateSplit]))
    return suite
