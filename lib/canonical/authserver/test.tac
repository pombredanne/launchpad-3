# Copyright 2004 Canonical Ltd.  All rights reserved.

from twisted.application import service, internet
from twisted.web import server
from twisted.enterprise.adbapi import ConnectionPool

from canonical.authserver.xmlrpc import UserDetailsResource
from canonical.authserver.database import DatabaseUserDetailsStorage


application = service.Application("authserver_test")
dbpool = ConnectionPool('psycopg', 'dbname=launchpad_test')
storage = DatabaseUserDetailsStorage(dbpool)
site = server.Site(UserDetailsResource(storage, debug=True))
internet.TCPServer(8999, site).setServiceParent(application)

