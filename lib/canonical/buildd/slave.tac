# Copyright Canonical Limited
# Author: Daniel Silverstone <daniel.silverstone@canonical.com>

# Buildd Slave implementation

from twisted.application import service, strports
from canonical.buildd import XMLRPCBuildDSlave

from twisted.web import server
from ConfigParser import ConfigParser

import os

conffile = os.environ.get('BUILDD_SLAVE_CONFIG', 'example.conf')

c = ConfigParser()
c.read(conffile)
slave = XMLRPCBuildDSlave(c)

application = service.Application('BuildDSlave')
builddslaveService = service.IServiceCollection(application)

slavesite = server.Site(slave)

strports.service(slave.slave._config.get("slave","bindport"), slavesite).setServiceParent(builddslaveService)

# You can interact with a running slave like this:
#
# python
# import xmlrpclib
# s = xmlrpclib.Server("http://localhost:8221/")
# s.echo("Hello World")
