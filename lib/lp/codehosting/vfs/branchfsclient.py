# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

"""Client code for the branch filesystem endpoint.

This code talks to the internal XML-RPC server for the branch filesystem.
"""

__metaclass__ = type
__all__ = [
    'BlockingProxy',
    'BranchFileSystemClient',
    'NotInCache',
    'trap_fault',
    ]

import time

from twisted.internet import defer
from twisted.web.xmlrpc import Fault

from lp.code.interfaces.codehosting import BRANCH_TRANSPORT


class BlockingProxy:

    def __init__(self, proxy):
        self._proxy = proxy

    def callRemote(self, method_name, *args):
        return getattr(self._proxy, method_name)(*args)


class NotInCache(Exception):
    """Raised when we try to get a path from the cache that's not present."""


class BranchFileSystemClient:
    """Wrapper for the branch filesystem endpoint for a particular user.

    This wrapper caches the results of calls to translatePath in order to
    avoid a large number of roundtrips. In the normal course of operation, our
    Bazaar transport translates virtual paths to real paths on disk using this
    client. It does this many, many times for a single Bazaar operation, so we
    cache the results here.
    """

    def __init__(self, branchfs_endpoint, user_id, expiry_time=None,
                 _now=time.time):
        """Construct a caching branchfs_endpoint.

        :param branchfs_endpoint: An XML-RPC proxy that implements callRemote.
        :param user_id: The database ID of the user who will be making these
            requests. An integer.
        """
        self._branchfs_endpoint = branchfs_endpoint
        self._cache = {}
        self._user_id = user_id
        self.expiry_time = expiry_time
        self._now = _now

    def _getMatchedPart(self, path, transport_tuple):
        """Return the part of 'path' that the endpoint actually matched."""
        trailing_length = len(transport_tuple[2])
        if trailing_length == 0:
            matched_part = path
        else:
            matched_part = path[:-trailing_length]
        return matched_part.rstrip('/')

    def _addToCache(self, transport_tuple, path):
        """Cache the given 'transport_tuple' results for 'path'.

        :return: the 'transport_tuple' as given, so we can use this as a
            callback.
        """
        (transport_type, data, trailing_path) = transport_tuple
        matched_part = self._getMatchedPart(path, transport_tuple)
        if transport_type == BRANCH_TRANSPORT:
            self._cache[matched_part] = (transport_type, data, self._now())
        return transport_tuple

    def _getFromCache(self, path):
        """Get the cached 'transport_tuple' for 'path'."""
        split_path = path.strip('/').split('/')
        for object_path, value in self._cache.iteritems():
            transport_type, data, inserted_time = value
            split_object_path = object_path.strip('/').split('/')
            if split_path[:len(split_object_path)] == split_object_path:
                if (self.expiry_time is not None
                    and self._now() > inserted_time + self.expiry_time):
                    del self._cache[object_path]
                    break
                trailing_path = '/'.join(split_path[len(split_object_path):])
                return (transport_type, data, trailing_path)
        raise NotInCache(path)

    def createBranch(self, branch_path):
        """Create a Launchpad `IBranch` in the database.

        This raises any Faults that might be raised by the branchfs_endpoint's
        `createBranch` method, so for more information see
        `IBranchFileSystem.createBranch`.

        :param branch_path: The path to the branch to create.
        :return: A `Deferred` that fires the ID of the created branch.
        """
        return defer.maybeDeferred(
            self._branchfs_endpoint.callRemote, 'createBranch', self._user_id,
            branch_path)

    def requestMirror(self, branch_id):
        """Mark a branch as needing to be mirrored.

        :param branch_id: The database ID of the branch.
        """
        return defer.maybeDeferred(
            self._branchfs_endpoint.callRemote,
            'requestMirror', self._user_id, branch_id)

    def translatePath(self, path):
        """Translate 'path'."""
        try:
            return defer.succeed(self._getFromCache(path))
        except NotInCache:
            deferred = defer.maybeDeferred(
                self._branchfs_endpoint.callRemote,
                'translatePath', self._user_id, path)
            deferred.addCallback(self._addToCache, path)
            return deferred


def trap_fault(failure, *fault_classes):
    """Trap a fault, based on fault code.

    :param failure: A Twisted L{Failure}.
    :param *fault_codes: `LaunchpadFault` subclasses.
    :raise Failure: if 'failure' is not a Fault failure, or if the fault code
        does not match the given codes.
    :return: The Fault if it matches one of the codes.
    """
    failure.trap(Fault)
    fault = failure.value
    if fault.faultCode in [cls.error_code for cls in fault_classes]:
        return fault
    raise failure
