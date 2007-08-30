# Copyright 2006 Canonical Ltd.  All rights reserved.

# Twisted Application Configuration file.
# Use with "twistd2.4 -y <file.tac>", e.g. "twistd -noy server.tac"

import os

from twisted.application import service, internet, strports
from twisted.web import server

from canonical.launchpad.daemons import tachandler
from canonical.launchpad.scripts.ftests.distributionmirror_http_server import (
    DistributionMirrorTestHTTPServer)


application = service.Application('DistributionMirrorTestHTTPServer')
httpserverService = service.IServiceCollection(application)

# Service that announces when the daemon is ready
tachandler.ReadyService().setServiceParent(httpserverService)

root = DistributionMirrorTestHTTPServer()
site = server.Site(root)
site.displayTracebacks = False
# XXX: The port 11375 is what we use in the URLs of our mirrors in sampledata,
# so we need to use the same here. -- Guilherme Salgado, 2007-01-30
strports.service("11375", site).setServiceParent(httpserverService)
