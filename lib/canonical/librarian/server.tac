# Twisted Application Configuration file.
# Use with "twistd -y <file.tac>", e.g. "twistd -noy server.tac"

from canonical.database.sqlbase import SQLBase
from sqlobject import connectionForURI
from canonical.lp import initZopeless

from twisted.application import service, internet

from canonical.librarian.libraryprotocol import FileUploadFactory
from canonical.librarian import storage, db
from canonical.librarian import web as fatweb
from twisted.web import server

# Connect to database
initZopeless()
application = service.Application('Librarian')
librarianService = service.IServiceCollection(application)

storage = storage.FatSamStorage('/tmp/fatsam', db.Library())

f = FileUploadFactory(storage)
internet.TCPServer(9090, f).setServiceParent(librarianService)

root = fatweb.LibraryFileResource(storage)
root.putChild('search', fatweb.DigestSearchResource(storage))
root.putChild('byalias', fatweb.AliasSearchResource(storage))
site = server.Site(root)
site.displayTracebacks = False
internet.TCPServer(8000, site).setServiceParent(librarianService)
