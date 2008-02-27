# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Useful tools for interacting with Twisted."""

__metaclass__ = type
__all__ = ['defer_to_thread']


import threading

from twisted.internet import defer, threads
from twisted.python.util import mergeFunctionMetadata


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
