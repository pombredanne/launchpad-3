# Copyright 2004 Canonical Ltd.  All rights reserved.

import tempfile
import shutil
import os

from twisted.application import service, internet
from twisted.web import server

from canonical.lp import initZopeless

from canonical.librarian.libraryprotocol import FileUploadFactory
from canonical.librarian import storage, db
from canonical.librarian import web as fatweb

# Connect to database
initZopeless(dbuser='librarian')

class TestTCPServer(internet.TCPServer):
    def __init__(self, port, factory, interface=None, filePrefix='twistd'):
        self.prefix = filePrefix
        internet.TCPServer.__init__(self, port, factory, interface=interface)

    def startService(self):
        internet.TCPServer.startService(self)
        f = open(self.prefix + '.port', 'w')
        f.write(str(self._port.getHost().port))
        f.close()
        f = open(self.prefix + '.ready', 'w')
        f.close()

    def stopService(self):
        os.remove(self.prefix + '.ready')
        os.remove(self.prefix + '.port')
        internet.TCPServer.stopService(self)

application = service.Application('librarian_test')
librarianService = service.IServiceCollection(application)

path = tempfile.mkdtemp()
import atexit
atexit.register(shutil.rmtree, path, ignore_errors=True)

storage = storage.FatSamStorage(path, db.Library())

f = FileUploadFactory(storage)
TestTCPServer(0, f, interface='127.0.0.1',
              filePrefix='upload').setServiceParent(librarianService)

root = fatweb.LibraryFileResource(storage)
root.putChild('search', fatweb.DigestSearchResource(storage))
root.putChild('byalias', fatweb.AliasSearchResource(storage))
site = server.Site(root)
site.displayTracebacks = False
TestTCPServer(0, site, interface='127.0.0.1',
              filePrefix='web').setServiceParent(librarianService)

