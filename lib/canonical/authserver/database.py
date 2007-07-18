# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DatabaseUserDetailsStorage',
    'DatabaseUserDetailsStorageV2',
    'DatabaseBranchDetailsStorage',
    ]

import datetime
import os

import transaction

from zope.component import getUtility
from zope.interface import implements
from zope.security.interfaces import Unauthorized

from canonical.launchpad.webapp import urlappend
from canonical.launchpad.webapp.authentication import SSHADigestEncryptor
from canonical.launchpad.scripts.supermirror_rewritemap import split_branch_id
from canonical.launchpad.interfaces import (
    UBUNTU_WIKI_URL, BranchCreationForbidden, IBranchSet, IPersonSet,
    IProductSet)
from canonical.launchpad.ftests import login, logout, ANONYMOUS
from canonical.database.sqlbase import (
    cursor, sqlvalues, clear_current_connection_cache)
from canonical.database.constants import UTC_NOW
from canonical.lp import dbschema
from canonical.config import config

from canonical.authserver.interfaces import (
    IBranchDetailsStorage, IHostedBranchStorage, IUserDetailsStorage,
    IUserDetailsStorageV2, READ_ONLY, WRITABLE)

from twisted.internet.threads import deferToThread
from twisted.python.util import mergeFunctionMetadata


def utf8(x):
    if isinstance(x, unicode):
        x = x.encode('utf-8')
    return x


def read_only_transaction(function):
    """Decorate 'function' by wrapping it in a transaction and Zope session."""
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
    """Decorate 'function' by wrapping it in a transaction and Zope session."""
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


class UserDetailsStorageMixin:
    """Functions that are shared between DatabaseUserDetailsStorage and
    DatabaseUserDetailsStorageV2"""

    def _getEmailAddresses(self, cursor, personID):
        """Get the email addresses for a person"""
        person = getUtility(IPersonSet).get(personID)
        emails = [person.preferredemail] + list(person.validatedemails)
        return (
            [person.preferredemail.email] +
            [email.email for email in person.validatedemails])

    def getSSHKeys(self, loginID):
        return deferToThread(self._getSSHKeysInteraction, loginID)

    @read_only_transaction
    def _getSSHKeysInteraction(self, loginID):
        """The interaction for getSSHKeys."""
        person_data = self._getPerson(cursor(), loginID)
        if person_data is None:
            return []
        person_id = person_data[0]
        person = getUtility(IPersonSet).get(person_id)
        return [
            (key.keytype.title, key.keytext)
            for key in person.sshkeys]

    def _getPerson(self, cursor, loginID):
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

        if person is None:
            return None

        if person.password:
            salt = saltFromDigest(person.password)
        else:
            salt = ''

        wikiname = getattr(person.ubuntuwiki, 'wikiname', None)
        return [person.id, person.displayname, person.name, person.password,
                wikiname] + [salt]


class DatabaseUserDetailsStorage(UserDetailsStorageMixin):
    """Launchpad-database backed implementation of IUserDetailsStorage"""
    # Note that loginID always refers to any name you can login with (an email
    # address, or a nickname, or a numeric ID), whereas personID always refers
    # to the numeric ID, which is the value found in Person.id in the database.
    implements(IUserDetailsStorage)

    def __init__(self, connectionPool):
        """Constructor.

        :param connectionPool: A twisted.enterprise.adbapi.ConnectionPool
        """
        self.connectionPool = connectionPool
        self.encryptor = SSHADigestEncryptor()

    def getUser(self, loginID):
        return deferToThread(self._getUserInteraction, loginID)

    @read_only_transaction
    def _getUserInteraction(self, loginID):
        """The interaction for getUser."""
        cur = cursor()
        row = self._getPerson(cur, loginID)
        try:
            personID, displayname, name, passwordDigest, wikiname, salt = row
        except TypeError:
            # No-one found
            return {}

        emailaddresses = self._getEmailAddresses(cur, personID)

        if wikiname is None:
            # None/nil isn't standard XML-RPC
            wikiname = ''

        return {
            'id': personID,
            'displayname': displayname,
            'emailaddresses': emailaddresses,
            'wikiname': wikiname,
            'salt': salt,
        }

    def authUser(self, loginID, sshaDigestedPassword):
        return deferToThread(
            self._authUserInteraction, loginID, sshaDigestedPassword)

    @read_only_transaction
    def _authUserInteraction(self, loginID, sshaDigestedPassword):
        """The interaction for authUser."""
        row = self._getPerson(cursor(), loginID)
        try:
            personID, displayname, name, passwordDigest, wikiname, salt = row
        except TypeError:
            # No-one found
            return {}

        if passwordDigest is None:
            # The user has no password, which means they can't login.
            return {}

        if passwordDigest.rstrip() != sshaDigestedPassword.rstrip():
            # Wrong password
            return {}

        emailaddresses = self._getEmailAddresses(cursor(), personID)

        if wikiname is None:
            # None/nil isn't standard XML-RPC
            wikiname = ''

        return {
            'id': personID,
            'displayname': displayname,
            'emailaddresses': emailaddresses,
            'wikiname': wikiname,
            'salt': salt,
        }


def saltFromDigest(digest):
    """Extract the salt from a SSHA digest.

    :param digest: base64-encoded digest
    """
    if isinstance(digest, unicode):
        # Make sure digest is a str, because unicode objects don't have a
        # decode method in python 2.3.  Base64 should always be representable in
        # ASCII.
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

    def _getTeams(self, personID):
        """Get list of teams a person is in.

        Returns a list of team dicts (see IUserDetailsStorageV2).
        """
        person_id = self._getPerson(cursor(), personID)[0]
        person = getUtility(IPersonSet).get(person_id)

        teams = [
            dict(id=person.id, name=person.name,
                 displayname=person.displayname)]

        return teams + [
            dict(id=team.id, name=team.name, displayname=team.displayname)
            for team in person.teams_participated_in]

    def getUser(self, loginID):
        return deferToThread(self._getUserInteraction, loginID)

    @read_only_transaction
    def _getUserInteraction(self, loginID):
        """The interaction for getUser."""
        row = self._getPerson(cursor(), loginID)
        try:
            personID, displayname, name, passwordDigest, wikiname = row
        except TypeError:
            # No-one found
            return {}

        emailaddresses = self._getEmailAddresses(cursor(), personID)

        if wikiname is None:
            # None/nil isn't standard XML-RPC
            wikiname = ''

        return {
            'id': personID,
            'displayname': displayname,
            'name': name,
            'emailaddresses': emailaddresses,
            'wikiname': wikiname,
            'teams': self._getTeams(personID),
        }

    def _getPerson(self, cursor, loginID):
        """Look up a person by loginID.

        The loginID will be first tried as an email address, then as a numeric
        ID, then finally as a nickname.

        :returns: a tuple of (person ID, display name, password, wikiname) or
            None if not found.
        """
        row = UserDetailsStorageMixin._getPerson(self, cursor, loginID)
        if row is None:
            return None
        else:
            # Remove the salt from the result; the v2 API doesn't include it.
            return row[:-1]

    def authUser(self, loginID, password):
        return deferToThread(self._authUserInteraction, loginID, password)

    @read_only_transaction
    def _authUserInteraction(self, loginID, password):
        """The interaction for authUser."""
        row = self._getPerson(cursor(), loginID)
        try:
            personID, displayname, name, passwordDigest, wikiname = row
        except TypeError:
            # No-one found
            return {}

        if not self.encryptor.validate(password, passwordDigest):
            # Wrong password
            return {}

        emailaddresses = self._getEmailAddresses(cursor(), personID)

        if wikiname is None:
            # None/nil isn't standard XML-RPC
            wikiname = ''

        return {
            'id': personID,
            'name': name,
            'displayname': displayname,
            'emailaddresses': emailaddresses,
            'wikiname': wikiname,
            'teams': self._getTeams(personID),
        }

    def getBranchesForUser(self, personID):
        """See IHostedBranchStorage."""
        return deferToThread(self._getBranchesForUserInteraction, personID)

    @read_only_transaction
    def _getBranchesForUserInteraction(self, personID):
        """The interaction for getBranchesForUser."""
        person = getUtility(IPersonSet).get(personID)
        login(person.preferredemail.email)
        try:
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
        finally:
            logout()

    def fetchProductID(self, productName):
        """See IHostedBranchStorage."""
        return deferToThread(self._fetchProductIDInteraction, productName)

    @read_only_transaction
    def _fetchProductIDInteraction(self, productName):
        """The interaction for fetchProductID."""
        product = getUtility(IProductSet).getByName(productName)
        if product is None:
            return ''
        else:
            return product.id

    def createBranch(self, loginID, personName, productName, branchName):
        """See IHostedBranchStorage."""
        return deferToThread(
            self._createBranchInteraction, loginID, personName, productName,
            branchName)

    @writing_transaction
    def _createBranchInteraction(self, loginID, personName, productName,
                                 branchName):
        """The interaction for createBranch."""
        requester_id = self._getPerson(cursor(), loginID)[0]
        requester = getUtility(IPersonSet).get(requester_id)
        login(requester.preferredemail.email)
        try:
            if productName == '+junk':
                product = None
            else:
                product = getUtility(IProductSet).getByName(productName)

            person_set = getUtility(IPersonSet)
            owner = person_set.getByName(personName)

            branch_set = getUtility(IBranchSet)
            try:
                branch = branch_set.new(
                    dbschema.BranchType.HOSTED, branchName, requester, owner,
                    product, None, None, author=requester)
            except BranchCreationForbidden:
                return ''
            else:
                return branch.id
        finally:
            logout()

    def requestMirror(self, branchID):
        """See IHostedBranchStorage."""
        return deferToThread(self._requestMirrorInteraction, branchID)

    @writing_transaction
    def _requestMirrorInteraction(self, branchID):
        """The interaction for requestMirror."""
        branch = getUtility(IBranchSet).get(branchID)
        branch.requestMirror()
        return True

    def getBranchInformation(self, loginID, userName, productName, branchName):
        """See IHostedBranchStorage."""
        return deferToThread(
            self._getBranchInformationInteraction, loginID, userName,
            productName, branchName)

    @read_only_transaction
    def _getBranchInformationInteraction(self, loginID, userName, productName,
                                         branchName):
        requester_id = self._getPerson(cursor(), loginID)[0]
        requester = getUtility(IPersonSet).get(requester_id)
        login(requester.preferredemail.email)
        try:
            branch = getUtility(IBranchSet).getByUniqueName(
                '~%s/%s/%s' % (userName, productName, branchName))
            if branch is None:
                return '', ''
            try:
                branch_id = branch.id
            except Unauthorized:
                return '', ''
            if requester.inTeam(branch.owner):
                return branch_id, WRITABLE
            else:
                return branch_id, READ_ONLY
        finally:
            logout()


class DatabaseBranchDetailsStorage:
    """Launchpad-database backed implementation of IUserDetailsStorage"""

    implements(IBranchDetailsStorage)

    def __init__(self, connectionPool):
        """Constructor.

        :param connectionPool: A twisted.enterprise.adbapi.ConnectionPool
        """
        self.connectionPool = connectionPool

    def getBranchPullQueue(self):
        ri = self.connectionPool.runInteraction
        return ri(self._getBranchPullQueueInteraction)

    def _getBranchPullQueueInteraction(self, transaction):
        """The interaction for getBranchPullQueue."""
        # The following types of branches are included in the queue:
        # - any branches which have not yet been mirrored
        # - any branches that were last mirrored over 6 hours ago
        # - any hosted branches which have requested that they be mirrored
        # - any import branches which have been synced since their last mirror

        # XXX: Hosted branches (see Andrew's comment dated 2006-06-15) are
        # mirrored if their mirror_request_time is not NULL or if they haven't
        # been mirrored in the last 6 hours. The latter behaviour is a
        # fail-safe and should probably be removed once we trust the
        # mirror_request_time behavior. See test_mirror_stale_hosted_branches.
        # -- jml, 2007-01-31

        # The mirroring interval is 6 hours. we think this is a safe balance
        # between frequency of mirroring and not hammering servers with
        # requests to check whether mirror branches are up to date.

        transaction.execute(utf8("""
            SELECT Branch.id, Branch.name, Branch.url, Person.name,
                   Product.name
            FROM Branch
            INNER JOIN Person ON Branch.owner = Person.id
            LEFT OUTER JOIN ProductSeries
                ON ProductSeries.import_branch = Branch.id
            LEFT OUTER JOIN Product
                ON Branch.product = Product.id
            WHERE
                (branch_type != %(imported)s AND
                    (last_mirror_attempt is NULL
                    OR (%(utc_now)s - last_mirror_attempt > '6 hours')
                    OR (branch_type = %(hosted)s
                        AND mirror_request_time IS NOT NULL)))
                OR (branch_type = %(hosted)s
                    AND mirror_request_time IS NOT NULL)
                OR (branch_type = %(imported)s
                    AND ((datelastsynced IS NOT NULL
                          AND last_mirror_attempt IS NULL) OR
                         (datelastsynced > last_mirror_attempt) OR
                         (datelastsynced IS NULL
                          AND (%(utc_now)s - last_mirror_attempt > '1 day'))))
            ORDER BY last_mirror_attempt IS NOT NULL, last_mirror_attempt
            """ % {'utc_now': UTC_NOW,
                   'hosted': dbschema.BranchType.HOSTED.value,
                   'imported': dbschema.BranchType.IMPORTED.value}))
        result = []
        for row in transaction.fetchall():
            branch_id, branch_name, url, owner_name, product_name = row
            # XXX - this logic is almost identical to that in
            # Branch.unique_name. Ideally, they should use the same code. Also,
            # it would be nice to guarantee that this points to a branch.
            # Jonathan Lange, 2007-03-01
            if product_name is None:
                product_name = u'+junk'
            unique_name = u'%s/%s/%s' % (owner_name, product_name, branch_name)

            if url is not None:
                # This is a pull branch, hosted externally.
                pull_url = url
            elif owner_name == 'vcs-imports':
                # This is an import branch, imported into bzr from
                # another RCS system such as CVS.
                prefix = config.launchpad.bzr_imports_root_url
                pull_url = urlappend(prefix, '%08x' % branch_id)
            else:
                # This is a push branch, hosted on the supermirror
                # (pushed there by users via SFTP).
                prefix = config.codehosting.branches_root
                pull_url = os.path.join(prefix, split_branch_id(branch_id))
            result.append((branch_id, pull_url, unique_name))
        return result

    def startMirroring(self, branchID):
        """See IBranchDetailsStorage"""
        return deferToThread(self._startMirroringInteraction, branchID)

    @writing_transaction
    def _startMirroringInteraction(self, branchID):
        """The interaction for startMirroring."""
        branch = getUtility(IBranchSet).get(branchID)
        if branch is None:
            return False
        branch.startMirroring()
        return True

    def mirrorComplete(self, branchID, lastRevisionID):
        """See IBranchDetailsStorage"""
        return deferToThread(
            self._mirrorCompleteInteraction, branchID, lastRevisionID)

    @writing_transaction
    def _mirrorCompleteInteraction(self, branchID, lastRevisionID):
        """The interaction for mirrorComplete."""
        branch = getUtility(IBranchSet).get(branchID)
        if branch is None:
            return False
        branch.mirrorComplete(lastRevisionID)
        return True

    def mirrorFailed(self, branchID, reason):
        """See IBranchDetailsStorage"""
        ri = self.connectionPool.runInteraction
        return ri(self._mirrorFailedInteraction, branchID, reason)

    def _mirrorFailedInteraction(self, transaction, branchID, reason):
        """The interaction for mirrorFailed."""
        transaction.execute(utf8("""
            UPDATE Branch
              SET mirror_failures = mirror_failures + 1,
                  mirror_status_message = %s, mirror_request_time = NULL
              WHERE id = %s""" % sqlvalues(reason, branchID)))
        # how many rows were updated?
        assert transaction.rowcount in [0, 1]
        return transaction.rowcount == 1

    def recordSuccess(self, name, hostname, date_started, date_completed):
        """See `IBranchDetailsStorage`."""
        ri = self.connectionPool.runInteraction
        return ri(self._recordSuccessInteraction,
                  name, hostname, date_started, date_completed)

    def _recordSuccessInteraction(self, transaction, name, hostname,
            started_tuple, completed_tuple):
        """The interaction for recordSuccess."""
        date_started = datetime_from_tuple(started_tuple)
        date_completed = datetime_from_tuple(completed_tuple)
        transaction.execute(utf8("""
            INSERT INTO ScriptActivity
              (name, hostname, date_started, date_completed)
              VALUES (%s, %s, %s, %s)""" % sqlvalues(
            name, hostname, date_started, date_completed)))
        return transaction.rowcount == 1


def datetime_from_tuple(time_tuple):
    """Create a datetime from a sequence that quacks like time.struct_time.

    The tm_isdst is (index 8) is ignored. The created datetime uses tzinfo=UTC.
    """
    [year, month, day, hour, minute, second, unused, unused, unused] = (
        time_tuple)
    return datetime.datetime(year, month, day, hour, minute, second)
