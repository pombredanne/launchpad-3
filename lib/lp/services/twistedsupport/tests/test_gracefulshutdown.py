# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for our graceful daemon shutdown support."""

__metaclass__ = type

from lp.testing import TestCase

from lp.services.twistedsupport import gracefulshutdown

from twisted.internet.protocol import Factory, Protocol


class TestConnTrackingFactoryWrapper(TestCase):

    def test_isAvailable_initial_state(self):
        ctf = gracefulshutdown.ConnTrackingFactoryWrapper(Factory())
        self.assertTrue(ctf.isAvailable())

    def test_allConnectionsDone_can_only_be_called_once(self):
        ctf = gracefulshutdown.ConnTrackingFactoryWrapper(Factory())
        d = ctf.allConnectionsDone()
        self.assertRaises(AssertionError, ctf.allConnectionsDone)

    def test_allConnectionsDone_when_no_connections(self):
        ctf = gracefulshutdown.ConnTrackingFactoryWrapper(Factory())
        self.was_fired = False
        self.assertTrue(ctf.isAvailable())
        d = ctf.allConnectionsDone()
        self.assertFalse(ctf.isAvailable())
        def cb(ignored):
            self.was_fired = True
        d.addCallback(cb)
        self.assertTrue(self.was_fired)

    def test_allConnectionsDone_when_exactly_one_connection(self):
        ctf = gracefulshutdown.ConnTrackingFactoryWrapper(Factory())
        # Make one connection
        p = Protocol()
        ctf.registerProtocol(p)
        d = ctf.allConnectionsDone()
        self.was_fired = False
        def cb(ignored):
            self.was_fired = True
        d.addCallback(cb)
        self.assertFalse(self.was_fired)
        ctf.unregisterProtocol(p)
        self.assertTrue(self.was_fired)

    def test_allConnectionsDone_when_more_than_one_connection(self):
        ctf = gracefulshutdown.ConnTrackingFactoryWrapper(Factory())
        # Make two connection
        p1 = Protocol()
        p2 = Protocol()
        ctf.registerProtocol(p1)
        ctf.registerProtocol(p2)
        d = ctf.allConnectionsDone()
        self.was_fired = False
        def cb(ignored):
            self.was_fired = True
        d.addCallback(cb)
        self.assertFalse(self.was_fired)
        ctf.unregisterProtocol(p1)
        self.assertFalse(self.was_fired)
        ctf.unregisterProtocol(p2)
        self.assertTrue(self.was_fired)

    def test_unregisterProtocol_before_allConnectionsDone(self):
        ctf = gracefulshutdown.ConnTrackingFactoryWrapper(Factory())
        p = Protocol()
        ctf.registerProtocol(p)
        ctf.unregisterProtocol(p)

