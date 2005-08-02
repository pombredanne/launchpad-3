# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

# Twisted Application Configuration file.
# Use with "twistd2.4 -y <file.tac>", e.g. "twistd -noy server.tac"

import os

from twisted.application import service, internet, strports
from twisted.web import server

from canonical.database.sqlbase import SQLBase
from canonical.lp import initZopeless
from canonical.config import config

from canonical.librarian.libraryprotocol import FileUploadFactory
from canonical.librarian import storage, db
from canonical.librarian import web as fatweb


# Connect to database
initZopeless(
    dbuser=config.librarian.dbuser,
    dbhost=config.dbhost,
    dbname=config.dbname,
    implicitBegin=False
    )

application = service.Application('Librarian')
librarianService = service.IServiceCollection(application)

path = config.librarian.server.root
storage = storage.LibrarianStorage(path, db.Library())

f = FileUploadFactory(storage)
uploadPort = str(config.librarian.upload_port)
strports.service(uploadPort, f).setServiceParent(librarianService)

if config.librarian.server.upstream_host:
    upstreamHost = config.librarian.server.upstream_host
    upstreamPort = int(config.librarian.server.upstream_port)
    print 'Using upstream librarian http://%s:%d' % (upstreamHost, upstreamPort)
else:
    upstreamHost = upstreamPort = None
root = fatweb.LibraryFileResource(storage, upstreamHost, upstreamPort)
root.putChild('search', fatweb.DigestSearchResource(storage))
site = server.Site(root)
site.displayTracebacks = False
webPort = str(config.librarian.download_port)
strports.service(webPort, site).setServiceParent(librarianService)
