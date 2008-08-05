# Copyright 2007 Canonical Ltd.  All rights reserved.

"""The branch details XML-RPC API."""

__metaclass__ = type
__all__ = [
    'BranchDetailsStorageAPI',
    'BranchFileSystemAPI',
    ]


import datetime
from xmlrpclib import Fault

import pytz

from zope.component import getUtility
from zope.interface import implements
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import login_person, logout
from canonical.launchpad.interfaces.branch import (
    BranchType, BranchCreationException, IBranchSet, UnknownBranchTypeError)
from canonical.launchpad.interfaces.codehosting import (
    IBranchDetailsStorage, IBranchFileSystem, LAUNCHPAD_SERVICES,
    NOT_FOUND_FAULT_CODE, PERMISSION_DENIED_FAULT_CODE, READ_ONLY, WRITABLE)
from canonical.launchpad.interfaces.person import IPersonSet
from canonical.launchpad.interfaces.product import IProductSet
from canonical.launchpad.interfaces.scriptactivity import IScriptActivitySet
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.webapp import LaunchpadXMLRPCView
from canonical.launchpad.webapp.interfaces import NotFoundError


UTC = pytz.timezone('UTC')


class BranchDetailsStorageAPI(LaunchpadXMLRPCView):
    """See `IBranchDetailsStorage`."""

    implements(IBranchDetailsStorage)

    def _getBranchPullInfo(self, branch):
        """Return information the branch puller needs to pull this branch.

        This is outside of the IBranch interface so that the authserver can
        access the information without logging in as a particular user.

        :return: (id, url, unique_name), where `id` is the branch database ID,
            `url` is the URL to pull from and `unique_name` is the
            `unique_name` property without the initial '~'.
        """
        branch = removeSecurityProxy(branch)
        if branch.branch_type == BranchType.REMOTE:
            raise AssertionError(
                'Remote branches should never be in the pull queue.')
        return (branch.id, branch.getPullURL(), branch.unique_name)

    def getBranchPullQueue(self, branch_type):
        """See `IBranchDetailsStorage`."""
        try:
            branch_type = BranchType.items[branch_type]
        except KeyError:
            raise UnknownBranchTypeError(
                'Unknown branch type: %r' % (branch_type,))
        branches = getUtility(IBranchSet).getPullQueue(branch_type)
        return [self._getBranchPullInfo(branch) for branch in branches]

    def mirrorComplete(self, branch_id, last_revision_id):
        """See `IBranchDetailsStorage`."""
        branch = getUtility(IBranchSet).get(branch_id)
        if branch is None:
            return False
        # See comment in startMirroring.
        removeSecurityProxy(branch).mirrorComplete(last_revision_id)
        return True

    def mirrorFailed(self, branch_id, reason):
        """See `IBranchDetailsStorage`."""
        branch = getUtility(IBranchSet).get(branch_id)
        if branch is None:
            return False
        # See comment in startMirroring.
        removeSecurityProxy(branch).mirrorFailed(reason)
        return True

    def recordSuccess(self, name, hostname, started_tuple, completed_tuple):
        """See `IBranchDetailsStorage`."""
        date_started = datetime_from_tuple(started_tuple)
        date_completed = datetime_from_tuple(completed_tuple)
        getUtility(IScriptActivitySet).recordSuccess(
            name=name, date_started=date_started,
            date_completed=date_completed, hostname=hostname)
        return True

    def startMirroring(self, branch_id):
        """See `IBranchDetailsStorage`."""
        branch = getUtility(IBranchSet).get(branch_id)
        if branch is None:
            return False
        # The puller runs as no user and may pull private branches. We need to
        # bypass Zope's security proxy to set the mirroring information.
        removeSecurityProxy(branch).startMirroring()
        return True


def datetime_from_tuple(time_tuple):
    """Create a datetime from a sequence that quacks like time.struct_time.

    The tm_isdst is (index 8) is ignored. The created datetime uses
    tzinfo=UTC.
    """
    [year, month, day, hour, minute, second, unused, unused, unused] = (
        time_tuple)
    return datetime.datetime(
        year, month, day, hour, minute, second, tzinfo=UTC)


def run_as_requester(function):
    """Decorate 'function' by logging in as the user identified by its first
    parameter, the `Person` object is then passed in to the function instead
    of the login ID.

    The exception is when the requesting login ID is `LAUNCHPAD_SERVICES`. In
    that case, we'll pass through the `LAUNCHPAD_SERVICES` variable and the
    method will do whatever security proxy hackery is required to provide read
    privileges to the Launchpad services.

    Assumes that 'function' is on an object that implements a '_getPerson'
    method similar to `UserDetailsStorageMixin._getPerson`.
    """
    def as_user(self, loginID, *args, **kwargs):
        if loginID == LAUNCHPAD_SERVICES:
            # Don't pass in an actual user. Instead pass in LAUNCHPAD_SERVICES
            # and expect `function` to use `removeSecurityProxy` or similar.
            return function(self, LAUNCHPAD_SERVICES, *args, **kwargs)
        requester = getUtility(IPersonSet).get(loginID)
        if requester is None:
            raise NotFoundError("No person with id %s." % loginID)
        login_person(requester)
        try:
            return function(self, requester, *args, **kwargs)
        finally:
            logout()
    as_user.__name__ = function.__name__
    as_user.__doc__ = function.__doc__
    return as_user


class BranchFileSystemAPI(LaunchpadXMLRPCView):
    """See `IBranchFileSystem`."""

    implements(IBranchFileSystem)

    @run_as_requester
    def createBranch(self, requester, personName, productName, branchName):
        """See `IBranchFileSystem`."""
        owner = getUtility(IPersonSet).getByName(personName)
        if owner is None:
            return Fault(
                NOT_FOUND_FAULT_CODE,
                "User/team %r does not exist." % personName)

        if productName == '+junk':
            product = None
        else:
            product = getUtility(IProductSet).getByName(productName)
            if product is None:
                return Fault(
                    NOT_FOUND_FAULT_CODE,
                    "Project %r does not exist." % productName)

        try:
            branch = getUtility(IBranchSet).new(
                BranchType.HOSTED, branchName, requester, owner,
                product, None, None, author=requester)
        except (BranchCreationException, LaunchpadValidationError), e:
            return Fault(PERMISSION_DENIED_FAULT_CODE, str(e))
        else:
            return branch.id

    def _canWriteToBranch(self, requester, branch):
        """Can `requester` write to `branch`?"""
        if requester == LAUNCHPAD_SERVICES:
            return False
        return (branch.branch_type == BranchType.HOSTED
                and requester.inTeam(branch.owner))

    @run_as_requester
    def getBranchInformation(self, requester, userName, productName,
                             branchName):
        """See `IBranchFileSystem`."""
        branch = getUtility(IBranchSet).getByUniqueName(
            '~%s/%s/%s' % (userName, productName, branchName))
        if branch is None:
            return '', ''
        if requester == LAUNCHPAD_SERVICES:
            branch = removeSecurityProxy(branch)
        try:
            branch_id = branch.id
        except Unauthorized:
            return '', ''
        if branch.branch_type == BranchType.REMOTE:
            # Can't even read remote branches.
            return '', ''
        if self._canWriteToBranch(requester, branch):
            permissions = WRITABLE
        else:
            permissions = READ_ONLY
        return branch_id, permissions

    @run_as_requester
    def getDefaultStackedOnBranch(self, requester, project_name):
        if project_name == '+junk':
            return ''
        product = getUtility(IProductSet).getByName(project_name)
        if product is None:
            return Fault(
                NOT_FOUND_FAULT_CODE,
                "Project %r does not exist." % project_name)
        branch = product.default_stacked_on_branch
        if branch is None:
            return ''
        try:
            unique_name = branch.unique_name
        except Unauthorized:
            return ''
        return '/' + unique_name
