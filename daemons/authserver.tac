# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# This configuration creates an XML-RPC service listening on port 8999.  It
# exposes two APIs:
#   - the version 1 API with salts + SSHA digests, at /
#   - and the version 2 API with clear text passwords, at /v2/
#
# e.g. http://localhost:8999/v2/ is the path the version 2 API.

from twisted.application import service, strports
from twisted.web import server, resource
from twisted.enterprise.adbapi import ConnectionPool

from canonical.authserver.xmlrpc import (
    UserDetailsResource, UserDetailsResourceV2, BranchDetailsResource)
from canonical.authserver.database import (
    DatabaseUserDetailsStorage, DatabaseUserDetailsStorageV2,
    DatabaseBranchDetailsStorage)
from canonical.launchpad.daemons.tachandler import ReadyService
from canonical.config import config

application = service.Application("authserver")
dbpool = ConnectionPool(
    'psycopg', 
    'dbname=%s host=%s user=%s' 
    % (config.dbname, config.dbhost, config.authserver.dbuser), 
    cp_reconnect=True)
root = resource.Resource()
versionOneAPI = UserDetailsResource(DatabaseUserDetailsStorage(dbpool))
versionTwoAPI = UserDetailsResourceV2(DatabaseUserDetailsStorageV2(dbpool))
branchAPI = BranchDetailsResource(DatabaseBranchDetailsStorage(dbpool))
root.putChild('', versionOneAPI)
root.putChild('RPC2', versionTwoAPI)
root.putChild('v2', versionTwoAPI)
root.putChild('branch', branchAPI)
site = server.Site(root)
svc = strports.service(config.authserver.port, site)
svc.setServiceParent(application)

ReadyService().setServiceParent(application)

