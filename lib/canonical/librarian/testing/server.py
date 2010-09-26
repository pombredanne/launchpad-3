# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Fixture for the librarians."""

__metaclass__ = type
__all__ = [
    'cleanupLibrarianFiles',
    'fillLibrarianFile',
    'LibrarianTestSetup',
    ]

import os
import shutil
import tempfile
import warnings

from fixtures import Fixture

import canonical
from canonical.config import config
from canonical.launchpad.daemons.tachandler import (
    get_pid_from_file,
    TacException,
    TacTestSetup,
    two_stage_kill,
    )
from canonical.librarian.storage import _relFileLocation


class LibrarianServerFixture(Fixture):
    """Set up librarian servers for use by functional tests.

    >>> from urllib import urlopen
    >>> from canonical.config import config

    >>> librarian_url = "http://%s:%d" % (
    ...     config.librarian.download_host,
    ...     config.librarian.download_port)
    >>> restricted_librarian_url = "http://%s:%d" % (
    ...     config.librarian.restricted_download_host,
    ...     config.librarian.restricted_download_port)

    >>> LibrarianTestSetup().setUp()

    Set a socket timeout, so that this test cannot hang indefinitely.

    >>> import socket
    >>> print socket.getdefaulttimeout()
    None
    >>> socket.setdefaulttimeout(1)

    After setUp() is called, two librarian instances are started. The
    regular one:

    >>> 'Copyright' in urlopen(librarian_url).read()
    True

    And the restricted one:

    >>> 'Copyright' in urlopen(restricted_librarian_url).read()
    True

    The librarian root is also available.

    >>> import os
    >>> os.path.isdir(config.librarian_server.root)
    True

    After tearDown() is called, both instances are shut down:

    >>> LibrarianTestSetup().tearDown()

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

    >>> LibrarianTestSetup().setUp()
    >>> 'Copyright' in urlopen(librarian_url).read()
    True

    Tidy up.

    >>> LibrarianTestSetup().tearDown()
    >>> socket.setdefaulttimeout(None)

    :ivar: pid pid of the external process.
    """

    def __init__(self):
        Fixture.__init__(self)
        self._pid = None
        self._setup = False
        """Track whether the fixture has been setup or not."""

    def setUp(self):
        """Start both librarian instances."""
        if (self._persistent_servers() and self.pid):
            return
        elif self.pid:
            # Found an existing, running librarian, but we're not trying to
            # reuse it. We cannot clean it up because we don't know that its
            # config is the same: all we know for sure is that its using the
            # same pid we wanted.
            warnings.warn("Stale librarian process (%s) found" % (self.pid,))
            two_stage_kill(self.pid)
            if self.pid:
                raise Exception("Could not kill stale librarian.")
            self._pid = None
        Fixture.setUp(self)
        self.setUpRoot()
        try:
            TacLibrarianTestSetup().setUp()
            self._read_pid()
        except TacException:
            # Remove the directory usually removed in tearDown.
            self.tearDownRoot()
            raise
        self._setup = True

    def tearDown(self):
        self.cleanUp()

    def cleanUp(self):
        """Shut downs both librarian instances."""
        if self._persistent_servers():
            return
        if not self._setup:
            warnings.warn("Attempt to tearDown inactive fixture.",
                DeprecationWarning, stacklevel=3)
            return
        try:
            TacLibrarianTestSetup().tearDown()
            self.tearDownRoot()
        finally:
            Fixture.cleanUp(self)

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
        return get_pid_from_file(TacLibrarianTestSetup().pidfile)

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

    def tearDownRoot(self):
        """Remove the librarian root archive."""
        if os.path.isdir(self.root):
            shutil.rmtree(self.root)


_global_fixture = LibrarianServerFixture()

def LibrarianTestSetup():
    """Support the stateless lie."""
    return _global_fixture


class TacLibrarianTestSetup(TacTestSetup):
    """Start the regular librarian instance."""

    def setUpRoot(self):
        """Taken care by LibrarianTestSetup."""

    def tearDownRoot(self):
        """Taken care by LibrarianTestSetup."""

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
    def _log_directory(self):
        # Since the root gets deleted after the tests complete, and since we
        # may still want to access the log file for post-mortem debugging, put
        # the log file in the parent directory of root, or the temporary
        # directory if that doesn't exist.
        log_directory = os.path.dirname(self.root)
        if os.path.isdir(log_directory):
            return log_directory
        else:
            return tempfile.tempdir

    @property
    def logfile(self):
        return os.path.join(self._log_directory, 'librarian.log')


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
