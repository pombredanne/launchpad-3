# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
#
# This configuration creates an XML-RPC service listening on port 8999.
# See canonical.launchpad.daemons.authserver for more information.

from twisted.application import service

from canonical.config import config
from canonical.launchpad.daemons.authserver import AuthserverService
from canonical.launchpad.daemons.tachandler import ReadyService
from canonical.launchpad.scripts import execute_zcml_for_scripts


# XXX: JonathanLange: 2008-03-31:
# Since r5793, the Launchpad configuration system has been fundamentally
# changed, and there is no clear way to tell the web database adapter to
# connect as a different user.
#
# We'll hack around this by overriding the name of the Launchpad user. This is
# OK, since we're only doing it for the authserver.
#
# This was added to allow us to safely revert r5793, which is suspected of
# causing serious performance regressions on the authserver.
config_data = dedent("""
    [database]
    dbuser: authserver
    """)
config.push('authserver', config_data)

execute_zcml_for_scripts(use_web_security=True)

application = service.Application("authserver")
svc = AuthserverService()
svc.setServiceParent(application)

ReadyService().setServiceParent(application)
