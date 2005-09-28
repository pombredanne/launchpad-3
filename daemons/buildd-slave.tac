# Copyright Canonical Limited
# Author: Daniel Silverstone <daniel.silverstone@canonical.com>

# Buildd Slave implementation
# XXX: dsilvers: 2005/01/21: Currently everything logged in the slave gets
# passed through to the twistd log too. this could get dangerous/big

from twisted.application import service, strports
from canonical.buildd import XMLRPCBuildDSlave, DebianBuildManager
from canonical.launchpad.daemons import tachandler

from twisted.web import server, resource, static
from ConfigParser import SafeConfigParser

import os

conffile = os.environ.get('BUILDD_SLAVE_CONFIG', 'buildd-slave-example.conf')

conf = SafeConfigParser()
conf.read(conffile)
slave = XMLRPCBuildDSlave(conf)

slave.registerBuilder(DebianBuildManager,"debian")

application = service.Application('BuildDSlave')
builddslaveService = service.IServiceCollection(application)

# Service that announces when the daemon is ready
tachandler.ReadyService().setServiceParent(builddslaveService)

root = resource.Resource()
root.putChild('', slave)
root.putChild('RPC2', slave)
root.putChild('filecache', static.File(conf.get('slave', 'filecache')))
slavesite = server.Site(root)

strports.service(slave.slave._config.get("slave","bindport"), 
                 slavesite).setServiceParent(builddslaveService)

# You can interact with a running slave like this:
# (assuming the slave is on localhost:8221)
#
# python
# import xmlrpclib
# s = xmlrpclib.Server("http://localhost:8221/")
# s.echo("Hello World")
