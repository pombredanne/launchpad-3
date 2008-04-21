# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Useful tools for interacting with Twisted."""

__metaclass__ = type
__all__ = ['defer_to_thread']


from twisted.internet import threads
from twisted.python.util import mergeFunctionMetadata

def defer_to_thread(function):
    """Run in a thread and return a Deferred that fires when done."""

    def decorated(*args, **kwargs):
        return threads.deferToThread(function, *args, **kwargs)

    return mergeFunctionMetadata(function, decorated)
