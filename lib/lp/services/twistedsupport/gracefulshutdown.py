# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Utilities for graceful shutdown of Twisted services."""

__metaclass__ = type
__all__ = [
    'ConnTrackingFactoryWrapper',
    'ShutdownCleanlyService',
    'ServerAvailableResource',
    'OrderedMultiService',
    ]


from twisted.application import service, strports
from twisted.protocols.policies import WrappingFactory
from twisted.internet.defer import (
    Deferred, gatherResults, maybeDeferred, inlineCallbacks)
from twisted.web import resource, server
from zope.interface import implements


class ConnTrackingFactoryWrapper(WrappingFactory):

    allConnectionsGone = None

    def isAvailable(self):
        return self.allConnectionsGone is None

    def stopFactory(self):
        WrappingFactory.stopFactory(self)
        self.allConnectionsGone = Deferred()
        if len(self.protocols) == 0:
            self.allConnectionsGone.callback(None)

    def unregisterProtocol(self, p):
        WrappingFactory.unregisterProtocol(self, p)
        if len(self.protocols) == 0:
            if self.allConnectionsGone is not None:
                self.allConnectionsGone.callback(None)


class ShutdownCleanlyService(service.MultiService):

    def __init__(self, factories):
        self.factories = factories
        service.MultiService.__init__(self)

    def stopService(self):
        d = maybeDeferred(service.MultiService.stopService, self)
        return d.addCallback(self._cbServicesStopped)

    def _cbServicesStopped(self, ignored):
        return gatherResults([f.allConnectionsGone for f in self.factories])


class ServerAvailableResource(resource.Resource):

    def __init__(self, tracked_factories):
        resource.Resource.__init__(self)
        self.tracked_factories = tracked_factories

    def _render_common(self, request):
        state = 'available'
        for tracked in self.tracked_factories:
            if not tracked.isAvailable():
                state = 'unavailable'
        if state == 'available':
            request.setResponseCode(200)
        else:
            request.setResponseCode(503)
        request.setHeader('Content-Type', 'text/plain')

    def render_GET(self, request):
        state = self._render_common(request)
        # Generate a bit of text for humans' benefit.
        tracked_connections = set()
        for tracked in self.tracked_factories:
            tracked_connections.update(tracked.protocols)
        return '%s\n\n%d connections: \n\n%s\n' % (
            state, len(tracked_connections),
            '\n'.join(
                [str(c.transport.getPeer()) for c in tracked_connections]))

    def render_HEAD(self, request):
        self._render_common(request)
        return ''


class OrderedMultiService(service.MultiService):
    """
    A service that starts services in the order they are attached, and stops
    them in reverse order (waiting for each to stop before stopping the next).
    """

    implements(service.IServiceCollection)

    @inlineCallbacks
    def stopService(self):
        service.Service.stopService(self) # intentionally skip MultiService.stopService
        while self.services:
            svc = self.services.pop()
            yield maybeDeferred(svc.stopService)


def make_web_status_service(strport, tracking_factories):
    server_available_resource = ServerAvailableResource(tracking_factories)
    web_root = resource.Resource()
    web_root.putChild('', server_available_resource)
    web_factory = server.Site(web_root)
    return strports.service(strport, web_factory)
