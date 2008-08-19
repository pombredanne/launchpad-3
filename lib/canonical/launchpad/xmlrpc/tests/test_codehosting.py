# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the internal codehosting API."""

__metaclass__ = type

import datetime
import pytz
import unittest

from bzrlib.tests import adapt_tests, TestScenarioApplier

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.launchpad.ftests import ANONYMOUS, login
from canonical.launchpad.interfaces.launchpad import ILaunchBag
from canonical.launchpad.interfaces.branch import (
    BranchType, IBranchSet, BRANCH_NAME_VALIDATION_ERROR_MESSAGE)
from canonical.launchpad.interfaces.scriptactivity import (
    IScriptActivitySet)
from canonical.launchpad.interfaces.codehosting import (
    NOT_FOUND_FAULT_CODE, PERMISSION_DENIED_FAULT_CODE, READ_ONLY, WRITABLE)
from canonical.launchpad.testing import (
    LaunchpadObjectFactory, TestCaseWithFactory)
from canonical.launchpad.webapp.interfaces import NotFoundError
from canonical.launchpad.xmlrpc.codehosting import (
    BranchFileSystem, BranchPuller, LAUNCHPAD_SERVICES, run_with_login)
from canonical.launchpad.xmlrpc import faults
from canonical.testing import DatabaseFunctionalLayer


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
        self.assertEqual(self.person.name, username)

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
        self.assertEqual(self.person.name, user.name)

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

    :ivar endpoint_factory: A nullary callable used to construct the endpoint.
        This variable is set by the `PullerEndpointScenarioApplier`.
    """

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.storage = self.endpoint_factory()
        self.factory = self.lp_factory_factory()
        self.branch_getter = self.branch_getter_factory()

    def assertFaultEqual(self, expected_fault, observed_fault):
        """Assert that `expected_fault` equals `observed_fault`."""
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
        self.assertIs(self.branch_getter(branch_id), None)
        return branch_id

    def test_startMirroring(self):
        # startMirroring updates last_mirror_attempt to 'now', leaves
        # last_mirrored alone and returns True when passed the id of an
        # existing branch.
        branch = self.factory.makeBranch()
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
        branch = self.factory.makeBranch()
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
        branch = self.factory.makeBranch()
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
        branch = self.factory.makeBranch()
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
        branch = self.factory.makeBranch(BranchType.HOSTED)

        # Request that branch be mirrored. This sets next_mirror_time.
        branch.requestMirror()

        # Simulate successfully mirroring the branch.
        self.storage.startMirroring(branch.id)
        self.storage.mirrorComplete(branch.id, self.factory.getUniqueString())

        self.assertIs(None, branch.next_mirror_time)

    def test_recordSuccess(self):
        # recordSuccess must insert the given data into ScriptActivity.
        started = datetime.datetime(2007, 07, 05, 19, 32, 1, tzinfo=UTC)
        completed = datetime.datetime(2007, 07, 05, 19, 34, 24, tzinfo=UTC)
        started_tuple = tuple(started.utctimetuple())
        completed_tuple = tuple(completed.utctimetuple())
        success = self.storage.recordSuccess(
            'test-recordsuccess', 'vostok', started_tuple, completed_tuple)
        self.assertEqual(True, success)

        activity = getUtility(IScriptActivitySet).getLastActivity(
            'test-recordsuccess')
        self.assertEqual('vostok', activity.hostname)
        self.assertEqual(started, activity.date_started)
        self.assertEqual(completed, activity.date_completed)

    def test_setStackedOnDefaultURLFragment(self):
        # setStackedOn records that one branch is stacked on another. One way
        # to find the stacked-on branch is by the URL fragment that's
        # generated as part of Launchpad's default stacking.
        stacked_branch = self.factory.makeBranch()
        stacked_on_branch = self.factory.makeBranch()
        self.storage.setStackedOn(
            stacked_branch.id, '/%s' % stacked_on_branch.unique_name)
        self.assertEqual(stacked_branch.stacked_on, stacked_on_branch)

    def test_setStackedOnExternalURL(self):
        # If setStackedOn is passed an external URL, rather than a URL
        # fragment, it will mark the branch as being stacked on the branch in
        # Launchpad registered with that external URL.
        stacked_branch = self.factory.makeBranch()
        stacked_on_branch = self.factory.makeBranch(BranchType.MIRRORED)
        self.storage.setStackedOn(stacked_branch.id, stacked_on_branch.url)
        self.assertEqual(stacked_branch.stacked_on, stacked_on_branch)

    def test_setStackedOnExternalURLWithTrailingSlash(self):
        # If setStackedOn is passed an external URL with a trailing slash, it
        # won't make a big deal out of it, it will treat it like any other
        # URL.
        stacked_branch = self.factory.makeBranch()
        stacked_on_branch = self.factory.makeBranch(BranchType.MIRRORED)
        url = stacked_on_branch.url + '/'
        self.storage.setStackedOn(stacked_branch.id, url)
        self.assertEqual(stacked_branch.stacked_on, stacked_on_branch)

    def test_setStackedOnBranchNotFound(self):
        # If setStackedOn can't find a branch for the given location, it will
        # return a Fault.
        stacked_branch = self.factory.makeBranch()
        url = self.factory.getUniqueURL()
        fault = self.storage.setStackedOn(stacked_branch.id, url)
        self.assertFaultEqual(faults.NoSuchBranch(url), fault)

    def test_setStackedOnNoBranchWithID(self):
        # If setStackedOn is called for a branch that doesn't exist, it will
        # return a Fault.
        stacked_on_branch = self.factory.makeBranch(BranchType.MIRRORED)
        branch_id = self.getUnusedBranchID()
        fault = self.storage.setStackedOn(branch_id, stacked_on_branch.url)
        self.assertFaultEqual(faults.NoBranchWithID(branch_id), fault)


class BranchPullQueueTest(TestCaseWithFactory):
    """Tests for the pull queue methods of `IBranchPuller`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(BranchPullQueueTest, self).setUp()
        self.storage = BranchPuller(None, None)

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
        branch = self.factory.makeBranch(branch_type)
        branch.requestMirror()
        # The pull queues contain branches that have next_mirror_time strictly
        # in the past, but requestMirror sets this field to UTC_NOW, so we
        # push the time back slightly here to get the branch to show up in the
        # queue.
        naked_branch = removeSecurityProxy(branch)
        naked_branch.next_mirror_time -= datetime.timedelta(seconds=1)
        return branch

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

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(BranchFileSystemTest, self).setUp()
        self.branchfs = BranchFileSystem(None, None)

    def assertFaultEqual(self, faultCode, faultString, fault):
        """Assert that `fault` has the passed-in attributes."""
        self.assertEqual(fault.faultCode, faultCode)
        self.assertEqual(fault.faultString, faultString)

    def test_createBranch(self):
        # createBranch creates a branch with the supplied details and the
        # caller as registrant.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct()
        name = self.factory.getUniqueString()
        branch_id = self.branchfs.createBranch(
            owner.id, owner.name, product.name, name)
        login(ANONYMOUS)
        branch = getUtility(IBranchSet).get(branch_id)
        self.assertEqual(owner, branch.owner)
        self.assertEqual(product, branch.product)
        self.assertEqual(name, branch.name)
        self.assertEqual(owner, branch.registrant)

    def test_createBranch_junk(self):
        # createBranch can create +junk branches.
        owner = self.factory.makePerson()
        name = self.factory.getUniqueString()
        branch_id = self.branchfs.createBranch(
            owner.id, owner.name, '+junk', name)
        login(ANONYMOUS)
        branch = getUtility(IBranchSet).get(branch_id)
        self.assertEqual(owner, branch.owner)
        self.assertEqual(None, branch.product)
        self.assertEqual(name, branch.name)
        self.assertEqual(owner, branch.registrant)

    def test_createBranch_bad_product(self):
        # Creating a branch for a non-existant product fails.
        owner = self.factory.makePerson()
        name = self.factory.getUniqueString()
        message = "Project 'no-such-product' does not exist."
        fault = self.branchfs.createBranch(
            owner.id, owner.name, 'no-such-product', name)
        self.assertFaultEqual(
            NOT_FOUND_FAULT_CODE, message, fault)

    def test_createBranch_other_user(self):
        # Creating a branch under another user's directory fails.
        creator = self.factory.makePerson()
        other_person = self.factory.makePerson()
        product = self.factory.makeProduct()
        name = self.factory.getUniqueString()
        message = ("%s cannot create branches owned by %s"
                   % (creator.displayname, other_person.displayname))
        fault = self.branchfs.createBranch(
            creator.id, other_person.name, product.name, name)
        self.assertFaultEqual(
            PERMISSION_DENIED_FAULT_CODE, message, fault)

    def test_createBranch_bad_name(self):
        # Creating a branch with an invalid name fails.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct()
        invalid_name = 'invalid name!'
        message = ("Invalid branch name %r. %s"
                   % (invalid_name, BRANCH_NAME_VALIDATION_ERROR_MESSAGE))
        fault = self.branchfs.createBranch(
            owner.id, owner.name, product.name, invalid_name)
        self.assertFaultEqual(
            PERMISSION_DENIED_FAULT_CODE, message, fault)

    def test_createBranch_bad_user(self):
        # Creating a branch under a non-existent user fails.
        owner = self.factory.makePerson()
        product = self.factory.makeProduct()
        name = self.factory.getUniqueString()
        message = "User/team 'no-one' does not exist."
        fault = self.branchfs.createBranch(
            owner.id, 'no-one', product.name, name)
        self.assertFaultEqual(
            NOT_FOUND_FAULT_CODE, message, fault)

    def test_createBranch_bad_user_bad_product(self):
        # If both the user and the product are not found, then the missing
        # user "wins" the error reporting race (as the url reads
        # ~user/product/branch).
        owner = self.factory.makePerson()
        name = self.factory.getUniqueString()
        message = "User/team 'no-one' does not exist."
        fault = self.branchfs.createBranch(
            owner.id, 'no-one', 'no-product', name)
        self.assertFaultEqual(
            NOT_FOUND_FAULT_CODE, message, fault)

    def test_getBranchInformation_owned(self):
        # When we get the branch information for one of our own hosted
        # branches (i.e. owned by us or by a team we are on), we get the
        # database id of the branch, and a flag saying that we can write to
        # that branch.
        requester = self.factory.makePerson()
        branch = self.factory.makeBranch(BranchType.HOSTED, owner=requester)
        branch_id, permissions = self.branchfs.getBranchInformation(
            requester.id, branch.owner.name, branch.product.name, branch.name)
        login(ANONYMOUS)
        self.assertEqual(branch.id, branch_id)
        self.assertEqual(WRITABLE, permissions)

    def test_getBranchInformation_nonexistent(self):
        # When we get the branch information for a non-existent branch, we get
        # a tuple of two empty strings (the empty string being an
        # approximation of 'None').
        requester_id = self.factory.getUniqueInteger()
        branch_id, permissions = self.branchfs.getBranchInformation(
            12, 'some-name', 'some-product', 'doesnt-exist')
        login(ANONYMOUS)
        self.assertEqual('', branch_id)
        self.assertEqual('', permissions)

    def test_getBranchInformation_unowned(self):
        # When we get the branch information for a branch that we don't own,
        # we get the database id and a flag saying that we can only read that
        # branch.
        requester = self.factory.makePerson()
        branch = self.factory.makeBranch()
        branch_id, permissions = self.branchfs.getBranchInformation(
            requester.id, branch.owner.name, branch.product.name, branch.name)
        login(ANONYMOUS)
        self.assertEqual(branch.id, branch_id)
        self.assertEqual(READ_ONLY, permissions)

    def test_getBranchInformation_mirrored(self):
        # Mirrored branches cannot be written to by the smartserver or SFTP
        # server.
        requester = self.factory.makePerson()
        branch = self.factory.makeBranch(BranchType.MIRRORED, owner=requester)
        branch_info = self.branchfs.getBranchInformation(
            requester.id, branch.owner.name, branch.product.name, branch.name)
        login(ANONYMOUS)
        self.assertEqual((branch.id, READ_ONLY), branch_info)

    def test_getBranchInformation_imported(self):
        # Imported branches cannot be written to by the smartserver or SFTP
        # server.
        requester = self.factory.makePerson()
        branch = self.factory.makeBranch(BranchType.IMPORTED, owner=requester)
        branch_info = self.branchfs.getBranchInformation(
            requester.id, branch.owner.name, branch.product.name, branch.name)
        login(ANONYMOUS)
        self.assertEqual((branch.id, READ_ONLY), branch_info)

    def test_getBranchInformation_remote(self):
        # Remote branches are not accessible by the smartserver or SFTP
        # server.
        requester = self.factory.makePerson()
        branch = self.factory.makeBranch(BranchType.REMOTE, owner=requester)
        branch_info = self.branchfs.getBranchInformation(
            requester.id, branch.owner.name, branch.product.name, branch.name)
        login(ANONYMOUS)
        self.assertEqual(('', ''), branch_info)

    def test_getBranchInformation_private(self):
        # When we get the branch information for a private branch that is
        # hidden to us, it is an if the branch doesn't exist at all.
        requester = self.factory.makePerson()
        branch = removeSecurityProxy(self.factory.makeBranch(private=True))
        branch_info = self.branchfs.getBranchInformation(
            requester.id, branch.owner.name, branch.product.name, branch.name)
        login(ANONYMOUS)
        self.assertEqual(('', ''), branch_info)

    def test_getBranchInformationAsLaunchpadServices(self):
        # The LAUNCHPAD_SERVICES special "user" has read-only access to all
        # branches.
        branch = self.factory.makeBranch()
        branch_info = self.branchfs.getBranchInformation(
            LAUNCHPAD_SERVICES, branch.owner.name, branch.product.name,
            branch.name)
        login(ANONYMOUS)
        self.assertEqual((branch.id, READ_ONLY), branch_info)

    def test_getBranchInformationForPrivateAsLaunchpadServices(self):
        # The LAUNCHPAD_SERVICES special "user" has read-only access to all
        # branches, even private ones.
        requester = self.factory.makePerson()
        branch = removeSecurityProxy(self.factory.makeBranch(private=True))
        branch_info = self.branchfs.getBranchInformation(
            LAUNCHPAD_SERVICES, branch.owner.name, branch.product.name,
            branch.name)
        login(ANONYMOUS)
        self.assertEqual((branch.id, READ_ONLY), branch_info)

    def _enableDefaultStacking(self, product):
        # Only products that are explicitly specified in
        # allow_default_stacking will have values for default stacked-on. Here
        # we add the just-created product to allow_default_stacking so we can
        # test stacking with private branches.
        section = (
            "[codehosting]\n"
            "allow_default_stacking: %s,%s"
            % (config.codehosting.allow_default_stacking, product.name))
        handle = self.factory.getUniqueString()
        config.push(handle, section)
        self.addCleanup(lambda: config.pop(handle))

    def _makeProductWithStacking(self):
        product = self.factory.makeProduct()
        self._enableDefaultStacking(product)
        return product

    def _makeProductWithDevFocus(self, private=False):
        """Make a stacking-enabled product with a development focus.

        :param private: Whether the development focus branch should be
            private.
        :return: The new Product and the new Branch.
        """
        product = self._makeProductWithStacking()
        branch = self.factory.makeBranch(product=product, private=private)
        series = removeSecurityProxy(product.development_focus)
        series.user_branch = branch
        return product, branch

    def test_getDefaultStackedOnBranch_invisible(self):
        # When the default stacked-on branch for a product is not visible to
        # the requesting user, then we return the empty string.
        requester = self.factory.makePerson()
        product, branch = self._makeProductWithDevFocus(private=True)
        stacked_on_url = self.branchfs.getDefaultStackedOnBranch(
            requester.id, product.name)
        self.assertEqual('', stacked_on_url)

    def test_getDefaultStackedOnBranch_private(self):
        # When the default stacked-on branch for a product is private but
        # visible to the requesting user, we return the URL to the branch
        # relative to the host.
        product, branch = self._makeProductWithDevFocus(private=True)
        # We want to know who owns it and what its name is. We are a test and
        # should be allowed to know such things.
        branch = removeSecurityProxy(branch)
        unique_name = branch.unique_name
        stacked_on_url = self.branchfs.getDefaultStackedOnBranch(
            branch.owner.id, product.name)
        self.assertEqual('/' + unique_name, stacked_on_url)

    def test_getDefaultStackedOnBranch_junk(self):
        # getDefaultStackedOnBranch returns the empty string for '+junk'.
        requester = self.factory.makePerson()
        branch = self.branchfs.getDefaultStackedOnBranch(
            requester.id, '+junk')
        self.assertEqual('', branch)

    def test_getDefaultStackedOnBranch_none_set(self):
        # getDefaultStackedOnBranch returns the empty string when there is no
        # branch set.
        requester = self.factory.makePerson()
        branch = self.branchfs.getDefaultStackedOnBranch(
            requester.id, 'firefox')
        self.assertEqual('', branch)

    def test_getDefaultStackedOnBranch_no_product(self):
        # getDefaultStackedOnBranch raises a Fault if there is no such
        # product.
        requester = self.factory.makePerson()
        product = 'no-such-product'
        fault = self.branchfs.getDefaultStackedOnBranch(requester.id, product)
        self.assertFaultEqual(
            NOT_FOUND_FAULT_CODE, 'Project %r does not exist.' % (product,),
            fault)

    def test_getDefaultStackedOnBranch(self):
        # getDefaultStackedOnBranch returns the relative URL of the default
        # stacked-on branch for the named product.
        requester = self.factory.makePerson()
        product, branch = self._makeProductWithDevFocus(private=False)
        branch_location = self.branchfs.getDefaultStackedOnBranch(
            requester.id, product.name)
        login(ANONYMOUS)
        self.assertEqual('/' + branch.unique_name, branch_location)

    def test_initialMirrorRequest(self):
        # The default 'next_mirror_time' for a newly created hosted branch
        # should be None.
        branch = self.factory.makeBranch(BranchType.HOSTED)
        self.assertIs(None, branch.next_mirror_time)

    def test_requestMirror(self):
        # requestMirror should set the next_mirror_time field to be the
        # current time.
        requester = self.factory.makePerson()
        branch = self.factory.makeBranch(BranchType.HOSTED)
        self.branchfs.requestMirror(requester.id, branch.id)
        self.assertSqlAttributeEqualsDate(
            branch, 'next_mirror_time', UTC_NOW)

    def test_requestMirror_private(self):
        # requestMirror can be used to request the mirror of a private branch.
        requester = self.factory.makePerson()
        branch = self.factory.makeBranch(owner=requester, private=True)
        branch = removeSecurityProxy(branch)
        self.branchfs.requestMirror(requester.id, branch.id)
        self.assertSqlAttributeEqualsDate(
            branch, 'next_mirror_time', UTC_NOW)


class PullerEndpointScenarioApplier(TestScenarioApplier):

    scenarios = [
        ('real',
         {'endpoint_factory': lambda: BranchPuller(None, None),
          'lp_factory_factory': lambda: LaunchpadObjectFactory(),
          'branch_getter_factory': lambda: getUtility(IBranchSet).get})]


def test_suite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    puller_tests = loader.loadTestsFromTestCase(BranchPullerTest)
    adapt_tests(puller_tests, PullerEndpointScenarioApplier(), suite)
    suite.addTests(
        map(loader.loadTestsFromTestCase,
            [TestRunWithLogin,
             BranchPullQueueTest,
             BranchFileSystemTest,
             ]))
    return suite
