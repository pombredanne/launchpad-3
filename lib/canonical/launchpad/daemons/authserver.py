# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Provides an authserver service.
NOMERGE - make this docstring betterer.
"""

__metaclass__ = type
__all__ = ['AuthserverSetup']


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

# NOMERGE - make authserver.tac use this

class AuthserverSetup:
    # NOMERGE - docstring here and on methods
    # NOMERGE - make this a service subclass

    def makeConnectionPool(self):
        if config.dbhost is None:
            dbhost = ''
        else:
            dbhost = 'host=' + config.dbhost
        dbpool = ConnectionPool('psycopg',
                                'dbname=%s %s user=%s'
                                % (config.dbname, dbhost,
                                   config.authserver.dbuser),
                                cp_reconnect=True)
        return dbpool

    def makeResource(self, dbpool, debug=False):
        root = resource.Resource()
        v1API = UserDetailsResource(DatabaseUserDetailsStorage(dbpool),
                                    debug=debug)
        v2API = UserDetailsResourceV2(DatabaseUserDetailsStorageV2(dbpool),
                                      debug=debug)
        branchAPI = BranchDetailsResource(DatabaseBranchDetailsStorage(dbpool),
                                          debug=debug)
        root.putChild('', v1API)
        root.putChild('RPC2', v2API)
        root.putChild('v2', v2API)
        root.putChild('branch', branchAPI)
        return root

    def makeService(self):
        site = server.Site(self.makeResource(self.makeConnectionPool()))
        return strports.service(config.authserver.port, site)


