# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DatabaseUserDetailsStorage',
    'DatabaseUserDetailsStorageV2',
    'DatabaseBranchDetailsStorage',
    ]

import datetime
import pytz

import transaction

from zope.component import getUtility
from zope.interface import implements
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp.authentication import SSHADigestEncryptor
from canonical.launchpad.database import ScriptActivity
from canonical.launchpad.interfaces import (
    BranchCreationException, BranchType, IBranchSet, IPersonSet, IProductSet,
    UnknownBranchTypeError)
from canonical.launchpad.ftests import login, logout, ANONYMOUS
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.database.sqlbase import clear_current_connection_cache

from canonical.authserver.interfaces import (
    IBranchDetailsStorage, IHostedBranchStorage, IUserDetailsStorage,
    IUserDetailsStorageV2, NOT_FOUND_FAULT_CODE, PERMISSION_DENIED_FAULT_CODE,
    READ_ONLY, WRITABLE)

from twisted.internet import defer
from twisted.internet.threads import deferToThread
from twisted.python.util import mergeFunctionMetadata
from twisted.web.xmlrpc import Fault


UTC = pytz.timezone('UTC')

def utf8(x):
    if isinstance(x, unicode):
        x = x.encode('utf-8')
    return x


def read_only_transaction(function):
    """Wrap 'function' in a transaction and Zope session."""
    def transacted(*args, **kwargs):
        transaction.begin()
        clear_current_connection_cache()
        login(ANONYMOUS)
        try:
            return function(*args, **kwargs)
        finally:
            logout()
            transaction.abort()
    return mergeFunctionMetadata(function, transacted)


def writing_transaction(function):
    """Wrap 'function' in a transaction and Zope session."""
    def transacted(*args, **kwargs):
        transaction.begin()
        clear_current_connection_cache()
        login(ANONYMOUS)
        try:
            ret = function(*args, **kwargs)
        except:
            logout()
            transaction.abort()
            raise
        logout()
        transaction.commit()
        return ret
    return mergeFunctionMetadata(function, transacted)


def run_as_requester(function):
    """Decorate 'function' by logging in as the user identified by its first
    parameter, the `Person` object is then passed in to the function instead of
    the login ID.

    Assumes that 'function' is on an object that implements a '_getPerson'
    method similar to `UserDetailsStorageMixin._getPerson`.
    """
    def as_user(self, loginID, *args, **kwargs):
        requester = self._getPerson(loginID)
        login(requester.preferredemail.email)
        try:
            return function(self, requester, *args, **kwargs)
        finally:
            logout()
    as_user.__name__ = function.__name__
    as_user.__doc__ = function.__doc__
    return as_user


class UserDetailsStorageMixin:
    """Functions that are shared between DatabaseUserDetailsStorage and
    DatabaseUserDetailsStorageV2"""

    def _getEmailAddresses(self, person):
        """Get the email addresses for a person"""
        emails = [person.preferredemail] + list(person.validatedemails)
        return (
            [person.preferredemail.email] +
            [email.email for email in person.validatedemails])

    def getSSHKeys(self, loginID):
        """See `IUserDetailsStorage`."""
        return deferToThread(self._getSSHKeysInteraction, loginID)

    @read_only_transaction
    def _getSSHKeysInteraction(self, loginID):
        """The synchronous implementation of `getSSHKeys`.

        See `IUserDetailsStorage`.
        """
        person = self._getPerson(loginID)
        if person is None:
            return []
        return [(key.keytype.title, key.keytext) for key in person.sshkeys]

    def _getPerson(self, loginID):
        """Look up a person by loginID.

        The loginID will be first tried as an email address, then as a numeric
        ID, then finally as a nickname.

        :returns: a `Person` or None if not found.
        """
        try:
            if not isinstance(loginID, unicode):
                # Refuse to guess encoding, so we decode as 'ascii'
                loginID = str(loginID).decode('ascii')
        except UnicodeDecodeError:
            return None

        person_set = getUtility(IPersonSet)

        # Try as email first.
        person = person_set.getByEmail(loginID)

        # If email didn't work, try as id.
        if person is None:
            try:
                person_id = int(loginID)
            except ValueError:
                pass
            else:
                person = person_set.get(person_id)

        # If id didn't work, try as nick-name.
        if person is None:
            person = person_set.getByName(loginID)

        return person

    def _getPersonDict(self, person):
        """Return a dict representing 'person' to be returned over XML-RPC.

        See `IUserDetailsStorage`.
        """
        if person is None:
            return {}

        if person.password:
            salt = saltFromDigest(person.password)
        else:
            salt = ''

        wikiname = getattr(person.ubuntuwiki, 'wikiname', '')
        return {
            'id': person.id,
            'displayname': person.displayname,
            'emailaddresses': self._getEmailAddresses(person),
            'wikiname': wikiname,
            'salt': salt,
        }

    def getUser(self, loginID):
        """See `IUserDetailsStorage`."""
        return deferToThread(self._getUserInteraction, loginID)

    @read_only_transaction
    def _getUserInteraction(self, loginID):
        """The interaction for getUser."""
        return self._getPersonDict(self._getPerson(loginID))


class DatabaseUserDetailsStorage(UserDetailsStorageMixin):
    """Launchpad-database backed implementation of IUserDetailsStorage"""
    # Note that loginID always refers to any name you can login with (an email
    # address, or a nickname, or a numeric ID), whereas personID always refers
    # to the numeric ID, which is the value found in Person.id in the
    # database.
    implements(IUserDetailsStorage)

    def __init__(self, connectionPool):
        """Constructor.

        :param connectionPool: A twisted.enterprise.adbapi.ConnectionPool
        """
        self.connectionPool = connectionPool
        self.encryptor = SSHADigestEncryptor()

    def authUser(self, loginID, sshaDigestedPassword):
        """See `IUserDetailsStorage`."""
        return deferToThread(
            self._authUserInteraction, loginID,
            sshaDigestedPassword.encode('base64'))

    @read_only_transaction
    def _authUserInteraction(self, loginID, sshaDigestedPassword):
        """Synchronous implementation of `authUser`.

        See `IUserDetailsStorage`.
        """
        person = self._getPerson(loginID)

        if person is None:
            return {}

        if person.password is None:
            # The user has no password, which means they can't login.
            return {}

        if person.password.rstrip() != sshaDigestedPassword.rstrip():
            # Wrong password
            return {}

        return self._getPersonDict(person)


def saltFromDigest(digest):
    """Extract the salt from a SSHA digest.

    :param digest: base64-encoded digest
    """
    if isinstance(digest, unicode):
        # Make sure digest is a str, because unicode objects don't have a
        # decode method in python 2.3. Base64 should always be representable
        # in ASCII.
        digest = digest.encode('ascii')
    return digest.decode('base64')[20:].encode('base64')


class DatabaseUserDetailsStorageV2(UserDetailsStorageMixin):
    """Launchpad-database backed implementation of IUserDetailsStorageV2"""
    implements(IHostedBranchStorage, IUserDetailsStorageV2)

    def __init__(self, connectionPool):
        """Constructor.

        :param connectionPool: A twisted.enterprise.adbapi.ConnectionPool
        """
        self.connectionPool = connectionPool
        self.encryptor = SSHADigestEncryptor()

    def _getTeams(self, person):
        """Get list of teams a person is in.

        Returns a list of team dicts (see IUserDetailsStorageV2).
        """
        teams = [
            dict(id=person.id, name=person.name,
                 displayname=person.displayname)]

        return teams + [
            dict(id=team.id, name=team.name, displayname=team.displayname)
            for team in person.teams_participated_in]

    def _getPersonDict(self, person):
        person_dict = UserDetailsStorageMixin._getPersonDict(self, person)
        if person_dict == {}:
            return {}
        del person_dict['salt']
        person_dict['name'] = person.name
        person_dict['teams'] = self._getTeams(person)
        return person_dict

    def authUser(self, loginID, password):
        """See `IUserDetailsStorageV2`."""
        return deferToThread(self._authUserInteraction, loginID, password)

    @read_only_transaction
    def _authUserInteraction(self, loginID, password):
        """Synchronous implementation of `authUser`.

        See `IUserDetailsStorageV2`.
        """
        person = self._getPerson(loginID)
        if person is None:
            return {}

        if not self.encryptor.validate(password, person.password):
            # Wrong password
            return {}

        return self._getPersonDict(person)

    def getBranchesForUser(self, personID):
        """See `IHostedBranchStorage`."""
        return deferToThread(self._getBranchesForUserInteraction, personID)

    @read_only_transaction
    @run_as_requester
    def _getBranchesForUserInteraction(self, person):
        """Synchronous implementation of `getBranchesForUser`.

        See `IHostedBranchStorage`.
        """
        branches = getUtility(
            IBranchSet).getHostedBranchesForPerson(person)
        branches_summary = {}
        for branch in branches:
            by_product = branches_summary.setdefault(branch.owner.id, {})
            if branch.product is None:
                product_id, product_name = '', ''
            else:
                product_id = branch.product.id
                product_name = branch.product.name
            by_product.setdefault((product_id, product_name), []).append(
                (branch.id, branch.name))
        return [(person_id, by_product.items())
                for person_id, by_product in branches_summary.iteritems()]

    def fetchProductID(self, productName):
        """See `IHostedBranchStorage`."""
        return deferToThread(self._fetchProductIDInteraction, productName)

    @read_only_transaction
    def _fetchProductIDInteraction(self, productName):
        """The synchronous implementation of `fetchProductID`.

        See `IHostedBranchStorage`.
        """
        product = getUtility(IProductSet).getByName(productName)
        if product is None:
            return ''
        else:
            return product.id

    def createBranch(self, loginID, personName, productName, branchName):
        """See `IHostedBranchStorage`."""
        return deferToThread(
            self._createBranchInteraction, loginID, personName, productName,
            branchName)

    @writing_transaction
    @run_as_requester
    def _createBranchInteraction(self, requester, personName, productName,
                                 branchName):
        """The synchronous implementation of `createBranch`.

        See `IHostedBranchStorage`.
        """

        owner = getUtility(IPersonSet).getByName(personName)
        if owner is None:
            raise Fault(
                NOT_FOUND_FAULT_CODE,
                "User/team %r does not exist." % personName)

        if productName == '+junk':
            product = None
        else:
            product = getUtility(IProductSet).getByName(productName)
            if product is None:
                raise Fault(
                    NOT_FOUND_FAULT_CODE,
                    "Project %r does not exist." % productName)

        try:
            branch = getUtility(IBranchSet).new(
                BranchType.HOSTED, branchName, requester, owner,
                product, None, None, author=requester)
        except (BranchCreationException, LaunchpadValidationError), e:
            raise Fault(PERMISSION_DENIED_FAULT_CODE, str(e))
        else:
            return branch.id

    def requestMirror(self, requester, branchID):
        """See `IHostedBranchStorage`."""
        return deferToThread(
            self._requestMirrorInteraction, requester, branchID)

    @writing_transaction
    @run_as_requester
    def _requestMirrorInteraction(self, requester, branchID):
        """The synchronous implementation of `requestMirror`.

        See `IHostedBranchStorage`.
        """
        branch = getUtility(IBranchSet).get(branchID)
        # We don't really care who requests a mirror of a branch.
        branch.requestMirror()
        return True

    def getDefaultStackedOnBranch(self, project_name):
        return deferToThread(
            self._getDefaultStackedOnBranchInteraction, project_name)

    @read_only_transaction
    def _getDefaultStackedOnBranchInteraction(self, project_name):
        if project_name == '+junk':
            return ''
        product = getUtility(IProductSet).getByName(project_name)
        branch = product.default_stacked_on_branch
        if branch is None:
            return ''
        else:
            return branch.unique_name

    def getBranchInformation(self, loginID, userName, productName,
                             branchName):
        """See `IHostedBranchStorage`."""
        return deferToThread(
            self._getBranchInformationInteraction, loginID, userName,
            productName, branchName)

    @read_only_transaction
    @run_as_requester
    def _getBranchInformationInteraction(self, requester, userName,
                                         productName, branchName):
        """The synchronous implementation of `getBranchInformation`.

        See `IHostedBranchStorage`.
        """
        branch = getUtility(IBranchSet).getByUniqueName(
            '~%s/%s/%s' % (userName, productName, branchName))
        if branch is None:
            return '', ''
        try:
            branch_id = branch.id
        except Unauthorized:
            return '', ''
        if (requester.inTeam(branch.owner)
            and branch.branch_type == BranchType.HOSTED):
            return branch_id, WRITABLE
        elif branch.branch_type == BranchType.REMOTE:
            # Can't even read remote branches.
            return '', ''
        else:
            return branch_id, READ_ONLY


class DatabaseBranchDetailsStorage:
    """Launchpad-database backed implementation of IUserDetailsStorage"""

    implements(IBranchDetailsStorage)

    def __init__(self, connectionPool):
        """Constructor.

        :param connectionPool: A twisted.enterprise.adbapi.ConnectionPool
        """
        self.connectionPool = connectionPool

    def _getBranchPullInfo(self, branch):
        """Return the information that the branch puller needs to pull this
        branch.

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
        return (branch.id, branch.getPullURL(), branch.unique_name[1:])

    def getBranchPullQueue(self, branch_type):
        """See `IBranchDetailsStorage`."""
        return deferToThread(self._getBranchPullQueueInteraction, branch_type)

    @read_only_transaction
    def _getBranchPullQueueInteraction(self, branch_type):
        """The synchronous implementation for `getBranchPullQueue`.

        See `IBranchDetailsStorage`.
        """
        try:
            branch_type = BranchType.items[branch_type]
        except KeyError:
            raise UnknownBranchTypeError(
                'Unknown branch type: %r' % (branch_type,))
        branches = getUtility(IBranchSet).getPullQueue(branch_type)
        return [self._getBranchPullInfo(branch) for branch in branches]

    def startMirroring(self, branchID):
        """See `IBranchDetailsStorage`."""
        return deferToThread(self._startMirroringInteraction, branchID)

    @writing_transaction
    def _startMirroringInteraction(self, branchID):
        """The synchronous implementation of `startMirroring`.

        See `IBranchDetailsStorage`.
        """
        branch = getUtility(IBranchSet).get(branchID)
        if branch is None:
            return False
        # The puller runs as no user and may pull private branches. We need to
        # bypass Zope's security proxy to set the mirroring information.
        removeSecurityProxy(branch).startMirroring()
        return True

    def mirrorComplete(self, branchID, lastRevisionID):
        """See `IBranchDetailsStorage`."""
        return deferToThread(
            self._mirrorCompleteInteraction, branchID, lastRevisionID)

    @writing_transaction
    def _mirrorCompleteInteraction(self, branchID, lastRevisionID):
        """The synchronous implementation of `mirrorComplete`.

        See `IBranchDetailsStorage`.
        """
        branch = getUtility(IBranchSet).get(branchID)
        if branch is None:
            return False
        # See comment in _startMirroringInteraction.
        removeSecurityProxy(branch).mirrorComplete(lastRevisionID)
        return True

    def mirrorFailed(self, branchID, reason):
        """See `IBranchDetailsStorage`."""
        return deferToThread(self._mirrorFailedInteraction, branchID, reason)

    @writing_transaction
    def _mirrorFailedInteraction(self, branchID, reason):
        """The synchronous implementation of `mirrorFailed`.

        See `IBranchDetailsStorage`.
        """
        branch = getUtility(IBranchSet).get(branchID)
        if branch is None:
            return False
        # See comment in _startMirroringInteraction.
        removeSecurityProxy(branch).mirrorFailed(reason)
        return True

    def recordSuccess(self, name, hostname, date_started, date_completed):
        """See `IBranchDetailsStorage`."""
        return deferToThread(
            self._recordSuccessInteraction, name, hostname, date_started,
            date_completed)

    @writing_transaction
    def _recordSuccessInteraction(self, name, hostname, started_tuple,
                                  completed_tuple):
        """The synchronous implementation of `recordSuccess`.

        See `IBranchDetailsStorage`.
        """
        date_started = datetime_from_tuple(started_tuple)
        date_completed = datetime_from_tuple(completed_tuple)
        ScriptActivity(
            name=name, hostname=hostname, date_started=date_started,
            date_completed=date_completed)
        return True


def datetime_from_tuple(time_tuple):
    """Create a datetime from a sequence that quacks like time.struct_time.

    The tm_isdst is (index 8) is ignored. The created datetime uses tzinfo=UTC.
    """
    [year, month, day, hour, minute, second, unused, unused, unused] = (
        time_tuple)
    return datetime.datetime(
        year, month, day, hour, minute, second, tzinfo=UTC)
