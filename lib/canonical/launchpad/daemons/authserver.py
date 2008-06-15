# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Provides an authserver service.

This service creates an XML-RPC service listening on port 8999.  It
exposes two APIs:
  - the version 1 API with salts + SSHA digests, at /
  - and the version 2 API with clear text passwords, at /v2/

e.g. http://localhost:8999/v2/ is the path the version 2 API.
"""

__metaclass__ = type
__all__ = ['AuthserverService']


from twisted.application import service, strports
from twisted.web import server, resource
from twisted.enterprise.adbapi import ConnectionPool

from canonical.authserver.xmlrpc import (
    UserDetailsResource, UserDetailsResourceV2, BranchDetailsResource)
from canonical.authserver.database import (
    DatabaseUserDetailsStorage, DatabaseUserDetailsStorageV2,
    DatabaseBranchDetailsStorage)
from canonical.config import config


class AuthserverService(service.Service):
    """Twisted service to run the authserver."""

    # XXX Jonathan Lange 2007-03-06:
    # This class' docstring should refer to some higher-level
    # documentation for the authserver, as it is likely to be one of the first
    # places a developer will look when trying to puzzle out the authserver.

    def __init__(self, dbpool=None, port=config.authserver.port):
        """Construct an AuthserverService.

        :param dbpool: An ADBAPI ConnectionPool to use for the authserver.
            If None, one is constructed based on settings in the Launchpad
            configuration.

        :param port: The port to run the server on, in Twisted
            strports format. Defaults to config.authserver.port.
        """
        if dbpool is None:
            self.dbpool = self._makeConnectionPool()
        self.port = port
        self.site = server.Site(self.makeResource(self.dbpool))
        self.service = strports.service(self.port, self.site)

    def _makeConnectionPool(self):
        """Construct a ConnectionPool from the database settings in the
        Launchpad config.
        """
        if config.database.dbhost is None:
            dbhost = ''
        else:
            dbhost = 'host=' + config.database.dbhost
        dbpool = ConnectionPool(
            'psycopg2', 'dbname=%s %s user=%s' % (
                config.database.dbname, dbhost, config.authserver.dbuser),
            cp_reconnect=True)
        return dbpool

    def buildTree(self, versionOneAPI, versionTwoAPI, branchAPI):
        """Take the XML-RPC resources and build a tree out of them."""
        root = resource.Resource()
        root.putChild('', versionOneAPI)
        root.putChild('RPC2', versionTwoAPI)
        root.putChild('v2', versionTwoAPI)
        root.putChild('branch', branchAPI)
        return root

    def makeResource(self, dbpool, debug=False):
        """Create and return a single resource which has all of our XML-RPC
        resources hanging off it as child nodes.
        """
        v1API = UserDetailsResource(DatabaseUserDetailsStorage(dbpool),
                                    debug=debug)
        v2API = UserDetailsResourceV2(DatabaseUserDetailsStorageV2(dbpool),
                                      debug=debug)
        branchAPI = BranchDetailsResource(
            DatabaseBranchDetailsStorage(dbpool), debug=debug)
        return self.buildTree(v1API, v2API, branchAPI)

    def startService(self):
        service.Service.startService(self)
        self.service.startService()

    def stopService(self):
        service.Service.stopService(self)
        self.dbpool.close()
        return self.service.stopService()
