# Copyright Canonical Limited
# Author: Daniel Silverstone <daniel.silverstone@canonical.com>

# Buildd Slave implementation
# XXX: dsilvers: 2005/01/21: Currently everything logged in the slave gets
# passed through to the twistd log too. this could get dangerous/big

from twisted.application import service, strports
from canonical.buildd import XMLRPCBuildDSlave, DebianBuildManager

from twisted.web import server
from ConfigParser import ConfigParser

import os

conffile = os.environ.get('BUILDD_SLAVE_CONFIG', 'buildd-slave-example.conf')

c = ConfigParser()
c.read(conffile)
slave = XMLRPCBuildDSlave(c)

slave.registerBuilder(DebianBuildManager,"debian")

application = service.Application('BuildDSlave')
builddslaveService = service.IServiceCollection(application)

slavesite = server.Site(slave)

strports.service(slave.slave._config.get("slave","bindport"), slavesite).setServiceParent(builddslaveService)

# You can interact with a running slave like this:
# (assuming the slave is on localhost:8221)
#
# python
# import xmlrpclib
# s = xmlrpclib.Server("http://localhost:8221/")
# s.echo("Hello World")
