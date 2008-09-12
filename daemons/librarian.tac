# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

# Twisted Application Configuration file.
# Use with "twistd2.4 -y <file.tac>", e.g. "twistd -noy server.tac"

from twisted.application import service, strports
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

path = config.librarian_server.root
if config.librarian_server.upstream_host:
    upstreamHost = config.librarian_server.upstream_host
    upstreamPort = config.librarian_server.upstream_port
    print 'Using upstream librarian http://%s:%d' % (
        upstreamHost, upstreamPort)
else:
    upstreamHost = upstreamPort = None

application = service.Application('Librarian')
librarianService = service.IServiceCollection(application)

# Service that announces when the daemon is ready
tachandler.ReadyService().setServiceParent(librarianService)

# Public librarian.
public_storage = storage.LibrarianStorage(path, db.Library(restricted=False))
uploadPort = config.librarian.upload_port
upload_factory = FileUploadFactory(public_storage)
strports.service(str(uploadPort), upload_factory).setServiceParent(
    librarianService)
root = fatweb.LibraryFileResource(public_storage, upstreamHost, upstreamPort)
root.putChild('search', fatweb.DigestSearchResource(public_storage))
root.putChild('robots.txt', fatweb.robotsTxt)
site = server.Site(root)
site.displayTracebacks = False
webPort = config.librarian.download_port
strports.service(str(webPort), site).setServiceParent(librarianService)

# Restricted librarian.
uploadPort = config.librarian.restricted_upload_port
restricted_storage = storage.LibrarianStorage(
    path, db.Library(restricted=True))
restricted_upload_factory = FileUploadFactory(restricted_storage)
strports.service(str(uploadPort), restricted_upload_factory).setServiceParent(
    librarianService)
root = fatweb.LibraryFileResource(
    restricted_storage, upstreamHost, upstreamPort)
root.putChild('search', fatweb.DigestSearchResource(restricted_storage))
root.putChild('robots.txt', fatweb.robotsTxt)
site = server.Site(root)
site.displayTracebacks = False
webPort = config.librarian.restricted_download_port
strports.service(str(webPort), site).setServiceParent(librarianService)
