# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

"""Client code for the branch filesystem endpoint.

This code talks to the internal XML-RPC server for the branch filesystem.
"""

__metaclass__ = type
__all__ = [
    'BlockingProxy',
    'CachingAuthserverClient',
    ]

import xmlrpclib

from twisted.internet import defer

from canonical.launchpad.interfaces.codehosting import (
    PERMISSION_DENIED_FAULT_CODE)


class BlockingProxy:

    def __init__(self, proxy):
        self._proxy = proxy

    def callRemote(self, method_name, *args):
        return getattr(self._proxy, method_name)(*args)


class CachingAuthserverClient:
    """Wrapper for the authserver that caches responses for a particular user.

    This only wraps the methods that are used for serving branches via a
    Bazaar transport: createBranch, getBranchInformation and requestMirror.

    In the normal course of operation, our Bazaar transport translates from
    "virtual branch identifier" (currently '~owner/product/name') to a branch
    ID. It does this many, many times for a single Bazaar operation. Thus, it
    makes sense to cache results from the authserver.
    """

    def __init__(self, authserver, user_id):
        """Construct a caching authserver.

        :param authserver: An XML-RPC proxy that implements callRemote.
        :param user_id: The database ID of the user who will be making these
            requests. An integer.
        """
        self._authserver = authserver
        self._branch_info_cache = {}
        self._stacked_branch_cache = {}
        self._user_id = user_id

    def createBranch(self, owner, product, branch):
        """Create a branch on the authserver.

        This raises any Faults that might be raised by the authserver's
        `createBranch` method, so for more information see
        `IHostedBranchStorage.createBranch`.

        :param owner: The owner of the branch. A string that is the name of a
            Launchpad `IPerson`.
        :param product: The project that the branch belongs to. A string that
            is either '+junk' or the name of a Launchpad `IProduct`.
        :param branch: The name of the branch to create.

        :return: A `Deferred` that fires the ID of the created branch.
        """
        deferred = defer.maybeDeferred(
            self._authserver.callRemote, 'createBranch', self._user_id,
            owner, product, branch)

        def clear_cache(branch_id):
            # Clear the cache for this branch. We *could* populate it with
            # (branch_id, 'w'), but then we'd be building in more assumptions
            # about the authserver.
            self._branch_info_cache[(owner, product, branch)] = None
            return branch_id

        return deferred.addCallback(clear_cache)

    def getBranchInformation(self, owner, product, branch):
        """Get branch information from the authserver.

        :param owner: The owner of the branch. A string that is the name of a
            Launchpad `IPerson`.
        :param product: The project that the branch belongs to. A string that
            is either '+junk' or the name of a Launchpad `IProduct`.
        :param branch: The name of the branch that we are interested in.

        :return: A Deferred that fires (branch_id, permissions), where
            'permissions' is WRITABLE if the current user can write to the
            branch, and READ_ONLY if they cannot. If the branch doesn't exist,
            return ('', ''). The "current user" is the user ID passed to the
            constructor.
        """
        branch_info = self._branch_info_cache.get((owner, product, branch))
        if branch_info is not None:
            return defer.succeed(branch_info)

        deferred = defer.maybeDeferred(
            self._authserver.callRemote, 'getBranchInformation',
            self._user_id, owner, product, branch)
        def add_to_cache(branch_info):
            self._branch_info_cache[
                (owner, product, branch)] = branch_info
            return branch_info
        return deferred.addCallback(add_to_cache)

    def getDefaultStackedOnBranch(self, product):
        branch_name = self._stacked_branch_cache.get(product)
        if branch_name is not None:
            return defer.succeed(branch_name)

        deferred = defer.maybeDeferred(
            self._authserver.callRemote, 'getDefaultStackedOnBranch',
            self._user_id, product)
        def add_to_cache(branch_name):
            self._stacked_branch_cache[product] = branch_name
            return branch_name
        return deferred.addCallback(add_to_cache)

    def requestMirror(self, branch_id):
        """Mark a branch as needing to be mirrored.

        :param branch_id: The database ID of the branch.
        """
        return defer.maybeDeferred(
            self._authserver.callRemote, 'requestMirror', self._user_id,
            branch_id)
