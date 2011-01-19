# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# This is a Twisted application config file.  To run, use:
#     twistd -noy sftp.tac
# or similar.  Refer to the twistd(1) man page for details.

from twisted.application import service
from twisted.protocols.policies import TimeoutFactory

from canonical.config import config
from canonical.launchpad.daemons import readyservice

from lp.codehosting.sshserver.daemon import (
    ACCESS_LOG_NAME, get_key_path, LOG_NAME, make_portal, OOPS_CONFIG_SECTION,
    PRIVATE_KEY_FILE, PUBLIC_KEY_FILE)
from lp.services.sshserver.service import SSHService
from lp.services.twistedsupport.gracefulshutdown import (
    ConnTrackingFactory, ServerAvailableResource, ShutdownCleanlyService,
    OrderedMultiService)


# Construct an Application that has the codehosting SSH server.
application = service.Application('sftponly')

ordered_services = OrderedMultiService()
ordered_services.setServiceParent(application)

tracked_factories = set()

def factory_decorator(factory):
    f = TimeoutFactory(factory, timeoutPeriod=config.codehosting.idle_timeout)
    f = ConnTrackingFactory(f)
    tracked_factories.add(f)
    return f


from twisted.application import strports
from twisted.web.resource import Resource
from twisted.web.server import Site
server_available_resource = ServerAvailableResource(tracked_factories)
web_root = Resource()
web_root.putChild('', server_available_resource)
web_factory = Site(web_root)
web_svc = strports.service('tcp:8768', web_factory)
web_svc.setServiceParent(ordered_services)

shutdown_cleanly_svc = ShutdownCleanlyService(
    tracked_factories, server_available_resource)
shutdown_cleanly_svc.setServiceParent(ordered_services)


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
