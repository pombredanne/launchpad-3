# Copyright 2009, 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# Author: Daniel Silverstone <daniel.silverstone@canonical.com>

# Buildd Slave implementation
# XXX: dsilvers: 2005/01/21: Currently everything logged in the slave gets
# passed through to the twistd log too. this could get dangerous/big

from twisted.application import service, strports
from canonical.buildd import XMLRPCBuildDSlave
from canonical.buildd.binarypackage import BinaryPackageBuildManager
from canonical.buildd.sourcepackagerecipe import (
    SourcePackageRecipeBuildManager)
from canonical.buildd.translationtemplates import TranslationTemplatesBuildManager
from canonical.launchpad.daemons import readyservice

from twisted.web import server, resource, static
from ConfigParser import SafeConfigParser

import os

conffile = os.environ.get('BUILDD_SLAVE_CONFIG', 'buildd-slave-example.conf')

conf = SafeConfigParser()
conf.read(conffile)
slave = XMLRPCBuildDSlave(conf)

# 'debian' is the old name. It remains here for compatibility.
slave.registerBuilder(BinaryPackageBuildManager, "debian")
slave.registerBuilder(BinaryPackageBuildManager, "binarypackage")
slave.registerBuilder(SourcePackageRecipeBuildManager, "sourcepackagerecipe")
slave.registerBuilder(TranslationTemplatesBuildManager, 'translation-templates')

application = service.Application('BuildDSlave')
builddslaveService = service.IServiceCollection(application)

# Service that announces when the daemon is ready
readyservice.ReadyService().setServiceParent(builddslaveService)

root = resource.Resource()
root.putChild('rpc', slave)
root.putChild('filecache', static.File(conf.get('slave', 'filecache')))
slavesite = server.Site(root)

strports.service(slave.slave._config.get("slave","bindport"), 
                 slavesite).setServiceParent(builddslaveService)

# You can interact with a running slave like this:
# (assuming the slave is on localhost:8221)
#
# python
# import xmlrpclib
# s = xmlrpclib.ServerProxy("http://localhost:8221/rpc")
# s.echo("Hello World")
