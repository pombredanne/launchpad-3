# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

import threading

from twisted.internet import defer, threads
from twisted.python.util import mergeFunctionMetadata
from twisted.web import xmlrpc

from zope.interface.interface import Method

from canonical.authserver.interfaces import (
    IBranchDetailsStorage, IUserDetailsStorage, IUserDetailsStorageV2)


def get_method_names_in_interface(interface):
    for attribute_name in interface:
        if isinstance(interface[attribute_name], Method):
            yield attribute_name


def defer_methods_to_threads(obj, interface):
    for name in get_method_names_in_interface(interface):
        setattr(obj, name, defer_to_thread(getattr(obj, name)))


def defer_to_thread(function):
    """Run in a thread and return a Deferred that fires when done."""

    def decorated(*args, **kwargs):
        deferred = defer.Deferred()

        def run_in_thread():
            return threads._putResultInDeferred(
                deferred, function, args, kwargs)

        t = threading.Thread(target=run_in_thread)
        t.start()
        return deferred

    return mergeFunctionMetadata(function, decorated)


class UserDetailsResource(xmlrpc.XMLRPC):

    def __init__(self, storage, debug=False):
        xmlrpc.XMLRPC.__init__(self)
        self.storage = storage
        defer_methods_to_threads(self.storage, IUserDetailsStorage)
        self.debug = debug

    def xmlrpc_getUser(self, loginID):
        """Get a user

        :returns: user dict if loginID exists, otherwise empty dict
        """
        if self.debug:
            print 'getUser(%r)' % (loginID,)
        return self.storage.getUser(loginID)

    def xmlrpc_authUser(self, loginID, sshaDigestedPassword):
        """Authenticate a user

        :returns: user dict if authenticated, otherwise empty dict
        """
        if self.debug:
            print 'authUser(%r, %r)' % (loginID, sshaDigestedPassword)
        return self.storage.authUser(loginID, sshaDigestedPassword)

    def xmlrpc_getSSHKeys(self, loginID):
        """Retrieve SSH public keys for a given user

        :param loginID: a login ID.
        :returns: list of 2-tuples of (key type, key text).  This list will be
            empty if the user has no keys or does not exist.

        :returns: user dict if loginID exists, otherwise empty dict
        """
        if self.debug:
            print 'getSSHKeys(%r)' % (loginID,)
        return self.storage.getSSHKeys(loginID)


class UserDetailsResourceV2(xmlrpc.XMLRPC):
    """A new (and simpler) version of the user details XML-RPC API."""

    def __init__(self, storage, debug=False):
        xmlrpc.XMLRPC.__init__(self)
        self.storage = storage
        defer_methods_to_threads(self.storage, IUserDetailsStorageV2)
        self.debug = debug

    def xmlrpc_getUser(self, loginID):
        """Get a user

        :returns: user dict if loginID exists, otherwise empty dict
        """
        if self.debug:
            print 'getUser(%r)' % (loginID,)
        return self.storage.getUser(loginID)

    def xmlrpc_authUser(self, loginID, password):
        """Authenticate a user

        :returns: user dict if authenticated, otherwise empty dict
        """
        if self.debug:
            print 'authUser(%r, %r)' % (loginID, password)
        return self.storage.authUser(loginID, password)

    def xmlrpc_getSSHKeys(self, loginID):
        """Retrieve SSH public keys for a given user

        :param loginID: a login ID.
        :returns: list of 2-tuples of (key type, key text).  This list will be
            empty if the user has no keys or does not exist.
        """
        if self.debug:
            print 'getSSHKeys(%r)' % (loginID,)
        return self.storage.getSSHKeys(loginID)

    def xmlrpc_getBranchesForUser(self, personID):
        """See IHostedBranchStorage."""
        if self.debug:
            print 'getBranchesForUser(%r)' % (personID,)
        return self.storage.getBranchesForUser(personID)

    def xmlrpc_fetchProductID(self, productName):
        """See IHostedBranchStorage."""
        if self.debug:
            print 'fetchProductID(%r)' % (productName,)
        return self.storage.fetchProductID(productName)

    def xmlrpc_createBranch(self, loginID, personName, productName,
                            branchName):
        """See IHostedBranchStorage."""
        if self.debug:
            print 'createBranch(%r, %r, %r, %r)' % (loginID, personName,
                                                    productName, branchName)
        return self.storage.createBranch(
            loginID, personName, productName, branchName)

    def xmlrpc_requestMirror(self, loginID, branchID):
        """See IHostedBranchStorage."""
        if self.debug:
            print 'requestMirror(%r, %r)' % (loginID, branchID)
        return self.storage.requestMirror(loginID, branchID)

    def xmlrpc_getBranchInformation(self, loginID, userName, productName,
                                    branchName):
        """See IHostedBranchStorage."""
        if self.debug:
            print 'getBranchInformation(%r, %r, %r, %r)' % (loginID,
                                                            userName,
                                                            productName,
                                                            branchName)
        return self.storage.getBranchInformation(
            loginID, userName, productName, branchName)


class BranchDetailsResource(xmlrpc.XMLRPC):

    def __init__(self, storage, debug=False):
        xmlrpc.XMLRPC.__init__(self)
        self.storage = storage
        defer_methods_to_threads(self.storage, IBranchDetailsStorage)
        self.debug = debug

    def xmlrpc_getBranchPullQueue(self, branch_type):
        if self.debug:
            print 'getBranchPullQueue(%r)' % (branch_type,)
        d = self.storage.getBranchPullQueue(branch_type)
        if self.debug:
            def printresult(result):
                for (branch_id, pull_url, unique_name) in result:
                    print branch_id, pull_url, unique_name
                return result
            d.addCallback(printresult)
        return d

    def xmlrpc_startMirroring(self, branchID):
        if self.debug:
            print 'startMirroring(%r)' % branchID
        d = self.storage.startMirroring(branchID)
        if self.debug:
            def printresult(result):
                print result
                return result
            d.addBoth(printresult)
        return d

    def xmlrpc_mirrorComplete(self, branchID, lastRevisionID):
        if self.debug:
            print 'mirrorComplete(%r, %r)' % (branchID, lastRevisionID)
        return self.storage.mirrorComplete(branchID, lastRevisionID)

    def xmlrpc_mirrorFailed(self, branchID, reason):
        if self.debug:
            print 'mirrorFailed(%r, %r)' % (branchID, reason)
        return self.storage.mirrorFailed(branchID, reason)

    def xmlrpc_recordSuccess(self, name, hostname,
                             date_started, date_completed):
        if self.debug:
            print 'recordSuccess(%r, %r, %r, %r)' % (
                name, hostname, date_started, date_completed)
        return self.storage.recordSuccess(
            name, hostname, date_started, date_completed)
