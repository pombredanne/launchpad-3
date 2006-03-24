# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Twisted TestCase that doesn't interfere with existing signal handlers."""

__metaclass__ = type


from unittest import TestSuite
import signal

from twisted.trial.unittest import TestCase as TrialTestCase


class TwistedTestCase(TrialTestCase):
    def run(self, result):
        # Record the signal handlers that Twisted will override (see
        # _handleSignals in twisted/internet/posixreactorbase.py).
        sigint = signal.getsignal(signal.SIGINT)
        sigterm = signal.getsignal(signal.SIGTERM)
        sigchld = signal.getsignal(signal.SIGCHLD)
        try:
            # TrialTestCase will start a reactor, which will install some signal
            # handlers.
            return TrialTestCase.run(self, result)
        finally:
            # Restore the original signal handlers
            signal.signal(signal.SIGINT, sigint)
            signal.signal(signal.SIGTERM, sigterm)
            signal.signal(signal.SIGCHLD, sigchld)

