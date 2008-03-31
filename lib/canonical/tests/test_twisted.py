# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0213

"""Twisted TestCase that doesn't interfere with existing signal handlers."""

__metaclass__ = type

import thread
from unittest import TestLoader

from canonical.testing import TwistedLayer
from canonical.twistedsupport import MethodDeferrer

from twisted.trial.unittest import TestCase as TrialTestCase

from zope.interface import implements, Interface


class IFoo(Interface):
    """Simple interface used in TestMethodDeferrer."""

    def simpleMethod(x):
        """Returns `x`."""

    def checkThreadID(self, main_thread_id):
        """Raise an error if the current thread is the main thread."""


class Foo:
    """Implements `IFoo` for TestMethodDeferrer."""

    implements(IFoo)

    def __init__(self):
        self.log = []

    def checkThreadID(self, main_thread_id):
        if thread.get_ident() == main_thread_id:
            raise AssertionError("Not running in thread")

    def simpleMethod(self, x):
        self.log.append(('foo', x))
        return x

    def notInInterface(self, x):
        self.log.append(('bar', x))
        return x


class TestMethodDeferrer(TrialTestCase):

    layer = TwistedLayer

    def setUp(self):
        self.original = Foo()
        self.wrapped = MethodDeferrer(self.original, IFoo)

    def checkLog(self, pass_through, expected_log):
        self.assertEqual(self.original.log, expected_log)
        return pass_through

    def test_callsUnderlying(self):
        # Calling a published method on an object wrapped with a
        # MethodDeferrer calls the underlying method.
        deferred = self.wrapped.simpleMethod(42)
        deferred.addCallback(self.assertEqual, 42)
        deferred.addCallback(self.checkLog, [('foo', 42)])
        return deferred

    def test_onlyAllowsPublishedMethods(self):
        # If you try to call a method that isn't advertised on an interface
        # provided to MethodDeferrer, you will get an AttributeError.
        self.assertRaises(
            AttributeError, lambda: self.wrapped.notInInterface(42))

    def test_checkRunningInThread(self):
        # Of course, the wrapped methods actually do run in separate threads.
        # We have to check this in a somewhat unusual way. The wrapped method
        # itself does the checking, as it is the only one that knows what
        # thread its in.
        main_thread_id = thread.get_ident()
        self.wrapped.checkThreadID(main_thread_id)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)


