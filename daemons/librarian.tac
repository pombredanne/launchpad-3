# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

# Twisted Application Configuration file.
# Use with "twistd2.4 -y <file.tac>", e.g. "twistd -noy server.tac"

import os

from twisted.application import service, internet, strports
from twisted.web import server

from canonical.config import config, dbconfig
from canonical.launchpad.daemons import tachandler
from canonical.launchpad.scripts import execute_zcml_for_scripts

from canonical.librarian.libraryprotocol import FileUploadFactory
from canonical.librarian import storage, db
from canonical.librarian import web as fatweb

# Connect to database
dbconfig.setConfigSection('librarian')
execute_zcml_for_scripts()

# Our version of twisted doesn't allow easily to add command-line
# parameters, so we use an environment variable to switch between
# starting the restricted or standard libarian.
restricted = 'RESTRICTED_LIBRARIAN' in os.environ
if restricted:
    applicationName = 'RestrictedLibrarian'
    uploadPort = config.librarian.restricted_upload_port
    webPort = config.librarian.restricted_download_port
else:
    applicationName = 'Librarian'
    uploadPort = config.librarian.upload_port
    webPort = config.librarian.download_port

application = service.Application(applicationName)
librarianService = service.IServiceCollection(application)

# Service that announces when the daemon is ready
tachandler.ReadyService().setServiceParent(librarianService)

path = config.librarian_server.root
storage = storage.LibrarianStorage(path, db.Library(restricted))

f = FileUploadFactory(storage)
strports.service(str(uploadPort), f).setServiceParent(librarianService)

if config.librarian_server.upstream_host:
    upstreamHost = config.librarian_server.upstream_host
    upstreamPort = config.librarian_server.upstream_port
    print 'Using upstream librarian http://%s:%d' % (
        upstreamHost, upstreamPort)
else:
    upstreamHost = upstreamPort = None
root = fatweb.LibraryFileResource(storage, upstreamHost, upstreamPort)
root.putChild('search', fatweb.DigestSearchResource(storage))
root.putChild('robots.txt', fatweb.robotsTxt)
site = server.Site(root)
site.displayTracebacks = False
strports.service(str(webPort), site).setServiceParent(librarianService)
