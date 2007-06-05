# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# This configuration creates an XML-RPC service listening on port 8999.
# See canonical.launchpad.daemons.authserver for more information.

from twisted.application import service
from canonical.launchpad.daemons.authserver import AuthserverService
from canonical.launchpad.daemons.tachandler import ReadyService

application = service.Application("authserver")
svc = AuthserverService()
svc.setServiceParent(application)

ReadyService().setServiceParent(application)
