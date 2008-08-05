# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the internal codehosting API."""

__metaclass__ = type

import datetime
import pytz
import transaction
import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import cursor
from canonical.launchpad.ftests import login, ANONYMOUS
from canonical.launchpad.interfaces.launchpad import ILaunchBag
from canonical.launchpad.interfaces.branch import (
    BranchType, IBranchSet, BRANCH_NAME_VALIDATION_ERROR_MESSAGE)
from canonical.launchpad.interfaces.person import IPersonSet
from canonical.launchpad.interfaces.scriptactivity import (
    IScriptActivitySet)
from canonical.launchpad.interfaces.codehosting import (
    NOT_FOUND_FAULT_CODE, PERMISSION_DENIED_FAULT_CODE, READ_ONLY, WRITABLE)
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp.interfaces import NotFoundError
from canonical.launchpad.xmlrpc.codehosting import (
    BranchDetailsStorageAPI, BranchFileSystemAPI, LAUNCHPAD_SERVICES,
    run_as_requester)
from canonical.testing import DatabaseFunctionalLayer


UTC = pytz.timezone('UTC')


def get_logged_in_username():
    """Return the username of the logged in person.

    Used by `TestRunAsRequester`.
    """
    user = getUtility(ILaunchBag).user
    if user is None:
        return None
    return user.name


class TestRunAsRequester(TestCaseWithFactory):
    """Tests for the `run_as_requester` decorator."""

    layer = DatabaseFunctionalLayer

    class UsesLogin:
        """Example class used for testing `run_as_requester`."""

        @run_as_requester
        def getLoggedInUsername(self, requester):
            return get_logged_in_username()

        @run_as_requester
        def getRequestingUser(self, requester):
            """Return the requester."""
            return requester

        @run_as_requester
        def raiseException(self, requester):
            raise RuntimeError("Deliberately raised error.")

    def setUp(self):
        super(TestRunAsRequester, self).setUp()
        self.person = self.factory.makePerson()
        transaction.commit()
        self.example = self.UsesLogin()

    def test_loginAsRequester(self):
        # run_as_requester logs in as user given as the first argument to the
        # method being decorated.
        username = self.example.getLoggedInUsername(self.person.id)
        self.assertEqual(self.person.name, username)

    def test_logoutAtEnd(self):
        # run_as_requester logs out once the decorated method is finished.
        self.example.getLoggedInUsername(self.person.id)
        self.assertEqual(None, get_logged_in_username())

    def test_logoutAfterException(self):
        # run_as_requester logs out even if the decorated method raises an
        # exception.
        try:
            self.example.raiseException(self.person.id)
        except RuntimeError:
            pass
        self.assertEqual(None, get_logged_in_username())

    def test_passesRequesterInAsPerson(self):
        # run_as_requester passes in the Launchpad Person object of the
        # requesting user.
        user = self.example.getRequestingUser(self.person.id)
        self.assertEqual(self.person.name, user.name)

    def test_invalidRequester(self):
        # A method wrapped with run_as_requester raises NotFoundError if there
        # is no person with the passed in id.
        self.assertRaises(
            NotFoundError, self.example.getRequestingUser, -1)

    def test_cheatsForLaunchpadServices(self):
        # Various Launchpad services need to use the authserver to get
        # information about branches, unencumbered by petty restrictions of
        # ownership or privacy. `run_as_requester` detects the special
        # username `LAUNCHPAD_SERVICES` and passes that through to the
        # decorated function without logging in.
        username = self.example.getRequestingUser(LAUNCHPAD_SERVICES)
        self.assertEqual(LAUNCHPAD_SERVICES, username)
        login_id = self.example.getLoggedInUsername(LAUNCHPAD_SERVICES)
        self.assertEqual(None, login_id)


class BranchDetailsStorageTest(TestCaseWithFactory):
    """Tests for the implementation of `IBranchDetailsStorage`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.storage = BranchDetailsStorageAPI(None, None)

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

    def test_startMirroring_invalid_branch(self):
        # startMirroring returns False when given a branch id which does not
        # exist.
        invalid_id = -1
        branch = getUtility(IBranchSet).get(invalid_id)
        self.assertIs(None, branch)

        success = self.storage.startMirroring(invalid_id)
        self.assertEqual(success, False)

    def test_mirrorFailed(self):
        branch = self.factory.makeBranch()
        self.assertUnmirrored(branch)

        self.storage.startMirroring(branch.id)
        failure_message = self.factory.getUniqueString()
        success = self.storage.mirrorFailed(branch.id, failure_message)
        self.assertEqual(success, True)
        self.assertMirrorFailed(branch, failure_message)

    def test_mirrorComplete(self):
        # mirrorComplete marks the branch as having been successfully
        # mirrored, with no failures and no status message.
        branch = self.factory.makeBranch()
        self.assertUnmirrored(branch)

        self.storage.startMirroring(branch.id)
        revision_id = self.factory.getUniqueString()
        success = self.storage.mirrorComplete(branch.id, revision_id)
        self.assertEqual(success, True)
        self.assertMirrorSucceeded(branch, revision_id)

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

    def test_recordSuccess(self):
        # recordSuccess must insert the given data into ScriptActivity.
        started = datetime.datetime(2007, 07, 05, 19, 32, 1, tzinfo=UTC)
        completed = datetime.datetime(2007, 07, 05, 19, 34, 24, tzinfo=UTC)
        started_tuple = tuple(started.utctimetuple())
        completed_tuple = tuple(completed.utctimetuple())
        success = self.storage.recordSuccess(
            'test-recordsuccess', 'vostok', started_tuple, completed_tuple)
        self.assertEqual(success, True)

        activity = getUtility(IScriptActivitySet).getLastActivity(
            'test-recordsuccess')
        self.assertEqual('vostok', activity.hostname)
        self.assertEqual(started, activity.date_started)
        self.assertEqual(completed, activity.date_completed)


class BranchPullQueueTest(TestCaseWithFactory):
    """Tests for the pull queue methods of `IBranchDetailsStorage`."""

    layer = DatabaseFunctionalLayer

    # XXX:
    # - Was it right to remove the switch to a more restrictive security
    #   proxy?

    def setUp(self):
        super(BranchPullQueueTest, self).setUp()
        self.storage = BranchDetailsStorageAPI(None, None)

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
        transaction.begin()
        try:
            branch = self.factory.makeBranch(branch_type)
            branch.requestMirror()
            return branch
        finally:
            transaction.commit()

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
        self.arbitrary_person = self.factory.makePerson()
        self.branchfs = BranchFileSystemAPI(None, None)

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
        branch_id, permissions = self.branchfs.getBranchInformation(
            requester.id, branch.owner.name, branch.product.name, branch.name)
        login(ANONYMOUS)
        self.assertEqual(branch.id, branch_id)
        self.assertEqual(READ_ONLY, permissions)

    def test_getBranchInformation_imported(self):
        # Imported branches cannot be written to by the smartserver or SFTP
        # server.
        requester = self.factory.makePerson()
        branch = self.factory.makeBranch(BranchType.IMPORTED, owner=requester)
        branch_id, permissions = self.branchfs.getBranchInformation(
            requester.id, branch.owner.name, branch.product.name, branch.name)
        login(ANONYMOUS)
        self.assertEqual(branch.id, branch_id)
        self.assertEqual(READ_ONLY, permissions)

    def test_getBranchInformation_remote(self):
        # Remote branches are not accessible by the smartserver or SFTP
        # server.
        requester = self.factory.makePerson()
        branch = self.factory.makeBranch(BranchType.REMOTE, owner=requester)
        branch_id, permissions = self.branchfs.getBranchInformation(
            requester.id, branch.owner.name, branch.product.name, branch.name)
        login(ANONYMOUS)
        self.assertEqual('', branch_id)
        self.assertEqual('', permissions)

    def test_getBranchInformation_private(self):
        # When we get the branch information for a private branch that is
        # hidden to us, it is an if the branch doesn't exist at all.
        requester = self.factory.makePerson()
        branch = removeSecurityProxy(self.factory.makeBranch(private=True))
        branch_id, permissions = self.branchfs.getBranchInformation(
            requester.id, branch.owner.name, branch.product.name, branch.name)
        login(ANONYMOUS)
        self.assertEqual('', branch_id)
        self.assertEqual('', permissions)

    def test_getBranchInformationAsLaunchpadServices(self):
        # The LAUNCHPAD_SERVICES special "user" has read-only access to all
        # branches.
        branch = self.factory.makeBranch()
        branch_id, permissions = self.branchfs.getBranchInformation(
            LAUNCHPAD_SERVICES, branch.owner.name, branch.product.name,
            branch.name)
        login(ANONYMOUS)
        self.assertEqual(branch.id, branch_id)
        self.assertEqual(READ_ONLY, permissions)

    def test_getBranchInformationForPrivateAsLaunchpadServices(self):
        # The LAUNCHPAD_SERVICES special "user" has read-only access to all
        # branches, even private ones.
        # salgado is a member of landscape-developers.
        requester = self.factory.makePerson()
        branch = removeSecurityProxy(self.factory.makeBranch(private=True))
        branch_info = self.branchfs.getBranchInformation(
            LAUNCHPAD_SERVICES, branch.owner.name, branch.product.name,
            branch.name)
        login(ANONYMOUS)
        self.assertEqual((branch.id, READ_ONLY), branch_info)

    def _makeProductWithPrivateDevFocus(self):
        """Make a product with a private development focus.

        :return: The new Product and the new Branch.
        """
        login(ANONYMOUS)
        product = self.factory.makeProduct()
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
        branch = self.factory.makeBranch(product=product)
        series = removeSecurityProxy(product.development_focus)
        series.user_branch = branch
        removeSecurityProxy(branch).private = True
        transaction.commit()
        logout()
        return product, branch

    def test_getDefaultStackedOnBranch_invisible(self):
        # When the default stacked-on branch for a product is not visible to
        # the requesting user, then we return the empty string.
        product, branch = self._makeProductWithPrivateDevFocus()
        stacked_on_url = self.branchfs.getDefaultStackedOnBranch(
            self.arbitrary_person.id, product.name)
        self.assertEqual('', stacked_on_url)

    def test_getDefaultStackedOnBranch_private(self):
        # When the default stacked-on branch for a product is private but
        # visible to the requesting user, we return the URL to the branch
        # relative to the host.
        product, branch = self._makeProductWithPrivateDevFocus()
        # We want to know who owns it and what its name is. We are a test and
        # should be allowed to know such things.
        branch = removeSecurityProxy(branch)
        unique_name = branch.unique_name
        stacked_on_url = self.branchfs.getDefaultStackedOnBranch(
            branch.owner.id, product.name)
        self.assertEqual('/' + unique_name, stacked_on_url)

    def test_getDefaultStackedOnBranch_junk(self):
        # getDefaultStackedOnBranch returns the empty string for '+junk'.
        branch = self.branchfs.getDefaultStackedOnBranch(
            self.arbitrary_person.id, '+junk')
        self.assertEqual('', branch)

    def test_getDefaultStackedOnBranch_none_set(self):
        # getDefaultStackedOnBranch returns the empty string when there is no
        # branch set.
        branch = self.branchfs.getDefaultStackedOnBranch(
            self.arbitrary_person.id, 'firefox')
        self.assertEqual('', branch)

    def test_getDefaultStackedOnBranch_no_product(self):
        # getDefaultStackedOnBranch raises a Fault if there is no such
        # product.
        product = 'no-such-product'
        self.assertRaisesFault(
            NOT_FOUND_FAULT_CODE,
            'Project %r does not exist.' % (product,),
            self.branchfs.getDefaultStackedOnBranch,
            self.arbitrary_person.id, product)

    def test_getDefaultStackedOnBranch(self):
        # getDefaultStackedOnBranch returns the relative URL of the default
        # stacked-on branch for the named product.
        branch = self.branchfs.getDefaultStackedOnBranch(
            self.arbitrary_person.id, 'evolution')
        self.assertEqual('/~vcs-imports/evolution/main', branch)

    def test_initialMirrorRequest(self):
        # The default 'next_mirror_time' for a newly created hosted branch
        # should be None.
        branchID = self.branchfs.createBranch(
            1, 'sabdfl', '+junk', 'foo')
        self.assertEqual(self.getNextMirrorTime(branchID), None)

    def test_requestMirror(self):
        # requestMirror should set the next_mirror_time field to be the
        # current time.
        hosted_branch_id = 25
        # make sure the sample data is sane
        self.assertEqual(None, self.getNextMirrorTime(hosted_branch_id))

        cur = cursor()
        cur.execute("SELECT CURRENT_TIMESTAMP AT TIME ZONE 'UTC'")
        [current_db_time] = cur.fetchone()
        transaction.commit()

        self.branchfs.requestMirror(1, hosted_branch_id)

        self.assertTrue(
            current_db_time < self.getNextMirrorTime(hosted_branch_id),
            "Branch next_mirror_time not updated.")

    def test_requestMirror_private(self):
        # requestMirror can be used to request the mirror of a private branch.

        # salgado is a member of landscape-developers.
        person_set = getUtility(IPersonSet)
        salgado = person_set.getByName('salgado')
        landscape_dev = person_set.getByName('landscape-developers')
        self.assertTrue(
            salgado.inTeam(landscape_dev),
            "salgado should be in landscape-developers team, but isn't.")

        branch_id = self.branchfs.createBranch(
            'salgado', 'landscape-developers', 'landscape',
            'some-branch')

        cur = cursor()
        cur.execute("SELECT CURRENT_TIMESTAMP AT TIME ZONE 'UTC'")
        [current_db_time] = cur.fetchone()
        transaction.commit()

        self.branchfs.requestMirror(salgado.id, branch_id)
        self.assertTrue(
            current_db_time < self.getNextMirrorTime(branch_id),
            "Branch next_mirror_time not updated.")


    def test_mirrorComplete_resets_mirror_request(self):
        # After successfully mirroring a branch, next_mirror_time should be
        # set to NULL.

        # An arbitrary hosted branch.
        hosted_branch_id = 25

        # The user id of a person who can see the hosted branch.
        user_id = 1

        # Request that 25 (a hosted branch) be mirrored. This sets
        # next_mirror_time.
        self.branchfs.requestMirror(user_id, hosted_branch_id)

        # Simulate successfully mirroring branch 25
        self.branchfs.startMirroring(hosted_branch_id)
        self.branchfs.mirrorComplete(hosted_branch_id, 'rev-1')

        self.assertEqual(None, self.getNextMirrorTime(hosted_branch_id))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

