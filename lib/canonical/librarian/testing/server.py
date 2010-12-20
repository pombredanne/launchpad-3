# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Fixture for the librarians."""

__metaclass__ = type
__all__ = [
    'cleanupLibrarianFiles',
    'fillLibrarianFile',
    'LibrarianServerFixture',
    'LibrarianTestSetup',
    ]

import atexit
import os
import shutil
import warnings

from fixtures import Fixture

import canonical
from canonical.config import config
from canonical.launchpad.daemons.tachandler import (
    get_pid_from_file,
    TacException,
    TacTestSetup,
    )
from canonical.librarian.storage import _relFileLocation


class LibrarianServerFixture(TacTestSetup):
    """Librarian server fixture.

    >>> from urllib import urlopen
    >>> from canonical.config import config

    >>> librarian_url = "http://%s:%d" % (
    ...     config.librarian.download_host,
    ...     config.librarian.download_port)
    >>> restricted_librarian_url = "http://%s:%d" % (
    ...     config.librarian.restricted_download_host,
    ...     config.librarian.restricted_download_port)

    >>> fixture = LibrarianServerFixture()
    >>> fixture.setUp()

    Set a socket timeout, so that this test cannot hang indefinitely.

    >>> import socket
    >>> print socket.getdefaulttimeout()
    None
    >>> socket.setdefaulttimeout(1)

    After setUp() is called, two librarian ports are available:
    The regular one:

    >>> 'Copyright' in urlopen(librarian_url).read()
    True

    And the restricted one:

    >>> 'Copyright' in urlopen(restricted_librarian_url).read()
    True

    The librarian root is also available.

    >>> import os
    >>> os.path.isdir(config.librarian_server.root)
    True

    After tearDown() is called, both ports are closed:

    >>> fixture.tearDown()

    >>> urlopen(librarian_url).read()
    Traceback (most recent call last):
    ...
    IOError: ...

    >>> urlopen(restricted_librarian_url).read()
    Traceback (most recent call last):
    ...
    IOError: ...

    The root directory was removed:

    >>> os.path.exists(config.librarian_server.root)
    False

    That fixture can be started and stopped multiple time in succession:

    >>> fixture.setUp()
    >>> 'Copyright' in urlopen(librarian_url).read()
    True

    Tidy up.

    >>> fixture.tearDown()
    >>> socket.setdefaulttimeout(None)

    :ivar: pid pid of the external process.
    """

    def __init__(self):
        Fixture.__init__(self)
        self._pid = None
        # Track whether the fixture has been setup or not.
        self._setup = False

    def setUp(self):
        """Start both librarian instances."""
        if (self._persistent_servers() and self.pid):
            return
        else:
            # self.pid may have been evaluated - nuke it.
            self._pid = None
        # The try:except here can be removed if someone audits the callers to
        # make sure that they call cleanUp if setUp fails.
        try:
            TacTestSetup.setUp(self)
        except TacException:
            self.cleanUp()
            raise
        else:
            self._pid = self._read_pid()
        self._setup = True
        self.addCleanup(setattr, self, '_setup', False)

    def cleanUp(self):
        """Shut downs both librarian instances."""
        if self._persistent_servers():
            return
        if not self._setup:
            warnings.warn("Attempt to tearDown inactive fixture.",
                DeprecationWarning, stacklevel=3)
            return
        TacTestSetup.cleanUp(self)

    def clear(self):
        """Clear all files from the Librarian"""
        # Make this smarter if our tests create huge numbers of files
        root = config.librarian_server.root
        if os.path.isdir(os.path.join(root, '00')):
            shutil.rmtree(os.path.join(root, '00'))

    @property
    def pid(self):
        if self._pid:
            return self._pid
        if self._persistent_servers():
            self._pid = self._read_pid()
        return self._pid

    def _read_pid(self):
        return get_pid_from_file(self.pidfile)

    def _persistent_servers(self):
        return os.environ.get('LP_PERSISTENT_TEST_SERVICES') is not None

    @property
    def root(self):
        """The root directory for the librarian file repository."""
        return config.librarian_server.root

    def setUpRoot(self):
        """Create the librarian root archive."""
        # This should not happen in normal usage, but might if someone
        # interrupts the test suite.
        if os.path.exists(self.root):
            self.tearDownRoot()
        os.makedirs(self.root, 0700)
        self.addCleanup(self.tearDownRoot)

    def tearDownRoot(self):
        """Remove the librarian root archive."""
        if os.path.isdir(self.root):
            shutil.rmtree(self.root)

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
        # Store the log in the server root; if its wanted after a test, that
        # test can use addDetail to grab the log and include it in its 
        # error.
        return os.path.join(self.root, 'librarian.log')

    def logChunks(self):
        """Get a list with the contents of the librarian log in it."""
        return open(self.logfile, 'rb').readlines()


_global_fixture = LibrarianServerFixture()


def LibrarianTestSetup():
    """Support the stateless lie."""
    return _global_fixture


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
    _global_fixture.clear()
