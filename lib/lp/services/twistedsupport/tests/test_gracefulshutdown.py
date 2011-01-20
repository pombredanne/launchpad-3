# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for our graceful daemon shutdown support."""

__metaclass__ = type

from lp.testing import TestCase

from lp.services.twistedsupport import gracefulshutdown

from twisted.application import service
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Factory, Protocol
from twisted.web import http


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


class TestServerAvailableResource(TestCase):

    def make_dummy_http_request(self):
        return http.Request('fake channel', True)

    def test_200_when_available(self):
        ctf = gracefulshutdown.ConnTrackingFactoryWrapper(Factory())
        r = gracefulshutdown.ServerAvailableResource([ctf])
        request = self.make_dummy_http_request()
        r.render_HEAD(request)
        self.assertEqual(200, request.code)
        # GET works too
        request = self.make_dummy_http_request()
        r.render_GET(request)
        self.assertEqual(200, request.code)

    def test_503_after_shutdown_starts(self):
        ctf = gracefulshutdown.ConnTrackingFactoryWrapper(Factory())
        r = gracefulshutdown.ServerAvailableResource([ctf])
        ctf.allConnectionsDone()
        request = self.make_dummy_http_request()
        r.render_HEAD(request)
        self.assertEqual(503, request.code)
        # GET works too
        request = self.make_dummy_http_request()
        r.render_GET(request)
        self.assertEqual(503, request.code)


class TestService(service.Service):

    def __init__(self, name, call_log):
        self.setName(name)
        self._call_log = call_log

    def startService(self):
        self._call_log.append(('startService', self.name))

    def stopService(self):
        self._call_log.append(('stopService', self.name))


class ServiceWithAsyncStop(service.Service):
    def __init__(self):
        self.stop_called = False
        self.stopDeferred = Deferred()
    def stopService(self):
        self.stop_called = True
        return self.stopDeferred


class TestOrderedMultiService(TestCase):

    def test_startService_starts_services_in_the_order_they_were_added(self):
        oms = gracefulshutdown.OrderedMultiService()
        call_log = []
        service1 = TestService('svc one', call_log)
        service1.setServiceParent(oms)
        service2 = TestService('svc two', call_log)
        service2.setServiceParent(oms)
        oms.startService()
        self.assertEqual(
            [('startService', 'svc one'), ('startService', 'svc two')],
            call_log)
        
    def test_stopService_stops_in_reverse_order(self):
        oms = gracefulshutdown.OrderedMultiService()
        call_log = []
        service1 = TestService('svc one', call_log)
        service1.setServiceParent(oms)
        service2 = TestService('svc two', call_log)
        service2.setServiceParent(oms)
        oms.startService()
        del call_log[:]
        d = oms.stopService()
        self.assertEqual(
            [('stopService', 'svc two'), ('stopService', 'svc one')],
            call_log)
        
    def test_services_are_stopped_in_series_not_parallel(self):
        oms = gracefulshutdown.OrderedMultiService()
        service1 = ServiceWithAsyncStop()
        service1.setServiceParent(oms)
        service2 = ServiceWithAsyncStop()
        service2.setServiceParent(oms)
        oms.startService()
        self.all_stopped = False
        def cb_all_stopped(ignored):
            self.all_stopped = True
        oms.stopService().addCallback(cb_all_stopped)
        self.assertFalse(self.all_stopped)
        self.assertFalse(service1.stop_called)
        self.assertTrue(service2.stop_called)
        service2.stopDeferred.callback(None)
        self.assertFalse(self.all_stopped)
        self.assertTrue(service1.stop_called)
        service1.stopDeferred.callback(None)
        self.assertTrue(self.all_stopped)
