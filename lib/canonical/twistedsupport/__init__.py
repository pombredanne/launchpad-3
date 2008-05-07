# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Useful tools for interacting with Twisted."""

__metaclass__ = type
__all__ = ['defer_to_thread', 'gatherResults']


from twisted.internet import defer, threads
from twisted.python.util import mergeFunctionMetadata


def defer_to_thread(function):
    """Run in a thread and return a Deferred that fires when done."""

    def decorated(*args, **kwargs):
        return threads.deferToThread(function, *args, **kwargs)

    return mergeFunctionMetadata(function, decorated)


def gatherResults(deferredList):
    """Returns list with result of given Deferreds.

    This builds on C{DeferredList} but is useful since you don't
    need to parse the result for success/failure.

    @type deferredList:  C{list} of L{Deferred}s
    """
    def convert_first_error_to_real(failure):
        failure.trap(defer.FirstError)
        return failure.value.subFailure

    d = defer.DeferredList(deferredList, fireOnOneErrback=1, consumeErrors=1)
    d.addCallback(defer._parseDListResult)
    d.addErrback(convert_first_error_to_real)
    return d

