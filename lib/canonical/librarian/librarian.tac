# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

# Twisted Application Configuration file.
# Use with "twistd2.3 -y <file.tac>", e.g. "twistd -noy server.tac"

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
    )

application = service.Application('Librarian')
librarianService = service.IServiceCollection(application)

path = config.librarian.server.root
storage = storage.LibrarianStorage(path, db.Library())

f = FileUploadFactory(storage)
uploadPort = str(config.librarian.upload_port)
strports.service(uploadPort, f).setServiceParent(librarianService)

root = fatweb.LibraryFileResource(storage)
root.putChild('search', fatweb.DigestSearchResource(storage))
root.putChild('byalias', fatweb.AliasSearchResource(storage))
site = server.Site(root)
site.displayTracebacks = False
webPort = str(config.librarian.download_port)
strports.service(webPort, site).setServiceParent(librarianService)
