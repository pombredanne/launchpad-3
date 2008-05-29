# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Useful tools for interacting with Twisted."""

__metaclass__ = type
__all__ = ['defer_to_thread', 'suppress_stderr']

import StringIO
import sys

from twisted.internet import defer, threads
from twisted.python.util import mergeFunctionMetadata


def defer_to_thread(function):
    """Run in a thread and return a Deferred that fires when done."""

    def decorated(*args, **kwargs):
        return threads.deferToThread(function, *args, **kwargs)

    return mergeFunctionMetadata(function, decorated)


def suppress_stderr(function):
    """Deferred friendly decorator that suppresses output from a function.
    """
    def set_stderr(result, stream):
        sys.stderr = stream
        return result

    def wrapper(*arguments, **keyword_arguments):
        saved_stderr = sys.stderr
        ignored_stream = StringIO.StringIO()
        sys.stderr = ignored_stream
        d = defer.maybeDeferred(function, *arguments, **keyword_arguments)
        return d.addBoth(set_stderr, saved_stderr)

    return mergeFunctionMetadata(function, wrapper)
