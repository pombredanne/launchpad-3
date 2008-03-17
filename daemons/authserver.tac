# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
#
# This configuration creates an XML-RPC service listening on port 8999.
# See canonical.launchpad.daemons.authserver for more information.

from twisted.application import service

from canonical.launchpad.daemons.authserver import AuthserverService
from canonical.launchpad.daemons.tachandler import ReadyService
from canonical.launchpad.scripts import execute_zcml_for_scripts

execute_zcml_for_scripts(use_web_security=True)

application = service.Application("authserver")
svc = AuthserverService()
svc.setServiceParent(application)

ReadyService().setServiceParent(application)
