# Twisted Application Configuration file.
# Use with "twistd -y <file.tac>", e.g. "twistd -noy server.tac"

import os

from twisted.application import service, internet, strports
from twisted.web import server

from canonical.database.sqlbase import SQLBase
from canonical.lp import initZopeless

from canonical.librarian.libraryprotocol import FileUploadFactory
from canonical.librarian import storage, db
from canonical.librarian import web as fatweb

# Connect to database
initZopeless()

application = service.Application('Librarian')
librarianService = service.IServiceCollection(application)

path = os.environ.get('LIBRARIAN_ROOT', '/tmp/fatsam')
storage = storage.FatSamStorage(path, db.Library())

f = FileUploadFactory(storage)
uploadPort = os.environ.get('LIBRARIAN_UPLOAD_PORT', '9090')
strports.service(uploadPort, f).setServiceParent(librarianService)

root = fatweb.LibraryFileResource(storage)
root.putChild('search', fatweb.DigestSearchResource(storage))
root.putChild('byalias', fatweb.AliasSearchResource(storage))
site = server.Site(root)
site.displayTracebacks = False
webPort = os.environ.get('LIBRARIAN_WEB_PORT', '8000')
strports.service(webPort, site).setServiceParent(librarianService)
