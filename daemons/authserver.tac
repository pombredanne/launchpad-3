# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# This configuration creates an XML-RPC service listening on port 8999.  It
# exposes two APIs:
#   - the version 1 API with salts + SSHA digests, at /
#   - and the version 2 API with clear text passwords, at /v2/
#
# e.g. http://localhost:8999/v2/ is the path the version 2 API.

from twisted.application import service, internet
from twisted.web import server, resource
from twisted.enterprise.adbapi import ConnectionPool

from canonical.authserver.xmlrpc import (
    UserDetailsResource, UserDetailsResourceV2, BranchDetailsResource)
from canonical.authserver.database import (
    DatabaseUserDetailsStorage, DatabaseUserDetailsStorageV2,
    DatabaseBranchDetailsStorage)


application = service.Application("authserver_test")
dbpool = ConnectionPool('psycopg', 'dbname=launchpad_dev')
storage = DatabaseUserDetailsStorage(dbpool)
root = resource.Resource()
versionOneAPI = UserDetailsResource(DatabaseUserDetailsStorage(dbpool))
versionTwoAPI = UserDetailsResourceV2(DatabaseUserDetailsStorageV2(dbpool), debug=True)
branchAPI = BranchDetailsResource(DatabaseBranchDetailsStorage(dbpool))
root.putChild('', versionOneAPI)
root.putChild('v2', versionTwoAPI)
root.putChild('branch', branchAPI)
site = server.Site(root)
internet.TCPServer(8999, site).setServiceParent(application)

