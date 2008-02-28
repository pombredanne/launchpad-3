# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Useful tools for interacting with Twisted."""

__metaclass__ = type
__all__ = ['defer_to_thread', 'MethodDeferrer']


from zope.interface.interface import Method

from twisted.internet import threads
from twisted.python.util import mergeFunctionMetadata


class MethodDeferrer:
    """Wraps an object's publihed methods in `defer_to_thread`."""

    def __init__(self, wrapped_object, *interfaces):
        self._original = wrapped_object
        self._published_methods = []
        for interface in interfaces:
            self._published_methods.extend(
                self._getMethodNamesInInterface(interface))

    def _getMethodNamesInInterface(self, interface):
        for attribute_name in interface:
            if isinstance(interface[attribute_name], Method):
                yield attribute_name

    def __getattr__(self, name):
        if name in self._published_methods:
            return defer_to_thread(getattr(self._original, name))
        raise AttributeError(name)


def defer_to_thread(function):
    """Run in a thread and return a Deferred that fires when done."""

    def decorated(*args, **kwargs):
        return threads.deferToThread(function, *args, **kwargs)

    return mergeFunctionMetadata(function, decorated)


