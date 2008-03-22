# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import os
import shutil

import canonical
from canonical.config import config
from canonical.launchpad.daemons.tachandler import TacTestSetup
from canonical.librarian.storage import _relFileLocation


class LibrarianTestSetup(TacTestSetup):
    r"""Set up a librarian for use by functional tests.

    >>> from urllib import urlopen
    >>> from canonical.config import config
    >>> host = config.librarian.download_host
    >>> port = config.librarian.download_port

    >>> LibrarianTestSetup().setUp()

    Set a socket timeout, so that this test cannot hang indefinitely.

    >>> import socket
    >>> print socket.getdefaulttimeout()
    None
    >>> socket.setdefaulttimeout(1)

    Make sure the server is running.

    >>> 'Copyright' in urlopen('http://%s:%d/' % (host, port)).read()
    True

    >>> LibrarianTestSetup().tearDown()

    Make sure it is not running
    >>> urlopen('http://%s:%d/' % (host, port))
    Traceback (most recent call last):
    ...
    IOError: ...

    And again for luck.

    >>> LibrarianTestSetup().setUp()
    >>> 'Copyright' in urlopen('http://%s:%d/' % (host, port)).read()
    True

    Tidy up.

    >>> LibrarianTestSetup().tearDown()
    >>> socket.setdefaulttimeout(None)

    """
    def setUpRoot(self):
        self.tearDownRoot()
        os.makedirs(self.root, 0700)

    def tearDownRoot(self):
        if os.path.isdir(self.root):
            shutil.rmtree(self.root)

    def clear(self):
        """Clear all files from the Librarian"""
        cleanupLibrarianFiles()

    @property
    def root(self):
        return config.librarian_server.root

    @property
    def tacfile(self):
        return os.path.abspath(os.path.join(
            os.path.dirname(canonical.__file__), os.pardir, os.pardir,
            'daemons/librarian.tac'
            ))

    @property
    def pidfile(self):
        return os.path.join(self.root, 'librarian.pid')

    @property
    def logfile(self):
        return os.path.join(self.root, 'librarian.log')


def fillLibrarianFile(fileid, content='Fake Content'):
    """Write contents in disk for a librarian sampledata."""
    filepath = os.path.join(
        config.librarian_server.root, _relFileLocation(fileid))

    if not os.path.exists(os.path.dirname(filepath)):
        os.makedirs(os.path.dirname(filepath))

    libfile = open(filepath, 'wb')
    libfile.write(content)
    libfile.close()

def cleanupLibrarianFiles():
    """Remove all librarian files present in disk."""
    # Make this smarter if our tests create huge numbers of files
    root = config.librarian_server.root
    if os.path.isdir(os.path.join(root, '00')):
        shutil.rmtree(os.path.join(root, '00'))
