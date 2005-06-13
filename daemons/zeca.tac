# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

# Twisted Application Configuration file.
# Use with "twistd2.3 -y <file.tac>", e.g. "twistd -noy server.tac"

from twisted.application import service, internet, strports
from twisted.web import server

from canonical.config import config

from canonical.zeca import Zeca, KeyServer, LookUp

application = service.Application('Zeca')
zecaService = service.IServiceCollection(application)

zeca = Zeca()
keyserver = KeyServer()
keyserver.putChild('lookup', LookUp(config.zeca.root))
zeca.putChild('pks', keyserver)
    
site = server.Site(zeca)
site.displayTracebacks = False
strports.service('11371', site).setServiceParent(zecaService)
