# Copyright 2004 Canonical Ltd.  All rights reserved.

from twisted.application import service, internet
from twisted.web import server
from twisted.enterprise.adbapi import ConnectionPool

from canonical.authserver.xmlrpc import UserDetailsResource
from canonical.authserver.database import DatabaseUserDetailsStorage
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
storage = DatabaseUserDetailsStorage(dbpool)
site = server.Site(UserDetailsResource(storage))
TestTCPServer(0, site, interface='127.0.0.1').setServiceParent(application)

