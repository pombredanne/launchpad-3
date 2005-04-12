# Copyright 2004 Canonical Ltd.  All rights reserved.

from twisted.application import service, internet
from twisted.web import server, resource
from twisted.enterprise.adbapi import ConnectionPool

from canonical.authserver.xmlrpc import UserDetailsResource
from canonical.authserver.database import DatabaseUserDetailsStorage
from canonical.authserver.xmlrpc import UserDetailsResourceV2
from canonical.authserver.database import DatabaseUserDetailsStorageV2
import canonical.lp

import os

class TestTCPServer(internet.TCPServer):
    def startService(self):
        internet.TCPServer.startService(self)
        f = open('twistd.port', 'w')
        f.write(str(self._port.getHost().port))
        f.close()
        f = open('twistd.ready', 'w')
        f.close()

    def stopService(self):
        os.remove('twistd.ready')
        os.remove('twistd.port')
        internet.TCPServer.stopService(self)

application = service.Application("authserver_test")
dbpool = ConnectionPool('psycopg', 'dbname=%s' % canonical.lp.dbname)
root = resource.Resource()
versionOneAPI = UserDetailsResource(DatabaseUserDetailsStorage(dbpool))
versionTwoAPI = UserDetailsResourceV2(DatabaseUserDetailsStorageV2(dbpool))
root.putChild('', versionOneAPI)
root.putChild('v2', versionTwoAPI)
site = server.Site(root)
TestTCPServer(0, site, interface='127.0.0.1').setServiceParent(application)

