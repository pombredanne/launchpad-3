# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# This is a Twisted application config file.  To run, use:
#     twistd -noy sftp.tac
# or similar.  Refer to the twistd(1) man page for details.

from twisted.application import service

from canonical.config import config
from canonical.launchpad.daemons import readyservice

from lp.codehosting.sshserver.daemon import (
    ACCESS_LOG_NAME, get_key_path, LOG_NAME, make_portal, OOPS_CONFIG_SECTION,
    PRIVATE_KEY_FILE, PUBLIC_KEY_FILE)
from lp.services.sshserver.service import SSHService


# Construct an Application that has the codehosting SSH server.
application = service.Application('sftponly')

from twisted.protocols.policies import TimeoutFactory, WrappingFactory
from twisted.internet.defer import Deferred, gatherResults, maybeDeferred
tracked_factories = set()

class ConnTrackingFactory(WrappingFactory):

    deferred = None

    def isAvailable(self):
        return self.deferred is None

    def allConnectionsDone(self):
        assert self.deferred is None
        self.deferred = Deferred()
        return self.deferred

    def unregisterProtocol(self, p):
        WrappingFactory.unregisterProtocol(self, p)
        if len(self.protocols) == 0:
            if self.deferred is not None:
                self.deferred.callback(None)


def factory_decorator(factory):
    f = TimeoutFactory(factory, timeoutPeriod=config.codehosting.idle_timeout)
    f = ConnTrackingFactory(f)
    tracked_factories.add(f)
    return f


class ShutdownCleanlyService(service.MultiService):

    def __init__(self, factories, server_available_resource):
        self.factories = factories
        self.server_available_resource = server_available_resource
        service.MultiService.__init__(self)

    def startService(self):
        d = maybeDeferred(service.MultiService.startService, self)
        def _cbStarted(ignored):
            self.server_available_resource.state = 'available'
        d.addCallback(_cbStarted)
        return d

    def stopService(self):
        self.server_available_resource.state = 'unavailable'
        d = maybeDeferred(service.MultiService.stopService, self)
        return d.addCallback(self._cbServicesStopped)

    def _cbServicesStopped(self, ignored):
        return gatherResults([f.allConnectionsDone() for f in self.factories])

from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.web.static import Data

web_root = Data('Codehosting status: see /status', 'text/plain')

class ServerAvailableResource(Resource):

    def __init__(self, tracked_factories):
        Resource.__init__(self)
        self.tracked_factories = tracked_factories

    def render_GET(self, request):
        state = 'available'
        for tracked in tracked_factories:
            if not tracked.isAvailable():
                state = 'unavailable'
        if state == 'available':
            request.setResponseCode(200)
        else:
            request.setResponseCode(503)
        request.setHeader('Content-Type', 'text/plain')
        tracked_connections = set()
        for tracked in tracked_factories:
            tracked_connections.update(tracked.protocols)
        return'%d connections: \n\n %s\n' % (len(tracked_connections),
                '\n'.join([str(c.transport.getPeer()) for c in
                    tracked_connections]))

from twisted.application import strports
server_available_resource = ServerAvailableResource(tracked_factories)
web_root.putChild('status', server_available_resource)
web_factory = Site(web_root)
web_svc = strports.service('tcp:8080', web_factory)

shutdown_cleanly_svc = ShutdownCleanlyService(
    tracked_factories, server_available_resource)
shutdown_cleanly_svc.setServiceParent(application)




svc = SSHService(
    portal=make_portal(),
    private_key_path=get_key_path(PRIVATE_KEY_FILE),
    public_key_path=get_key_path(PUBLIC_KEY_FILE),
    oops_configuration=OOPS_CONFIG_SECTION,
    main_log=LOG_NAME,
    access_log=ACCESS_LOG_NAME,
    access_log_path=config.codehosting.access_log,
    strport=config.codehosting.port,
    factory_decorator=factory_decorator,
    banner=config.codehosting.banner)
svc.setServiceParent(shutdown_cleanly_svc)

# Service that announces when the daemon is ready
readyservice.ReadyService().setServiceParent(application)
