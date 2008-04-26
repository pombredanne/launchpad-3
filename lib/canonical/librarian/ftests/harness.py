# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

"""Fixture for the librarians."""

__metaclass__ = type
__all__ = [
    'cleanupLibrarianFiles',
    'fillLibrarianFile',
    'LibrarianTestSetup',
    ]

import os
import shutil

import canonical
from canonical.config import config
from canonical.launchpad.daemons.tachandler import TacException, TacTestSetup
from canonical.librarian.storage import _relFileLocation


class LibrarianTestSetup:
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
    """

    def setUp(self):
        """Start both librarian instances."""
        self.setUpRoot()
        try:
            TacLibrarianTestSetup().setUp()
        except TacException:
            # Remove the directory usually removed in tearDown.
            self.tearDownRoot()
            raise

        try:
            TacRestrictedLibrarianTestSetup().setUp()
        except TacException:
            # Tear-down the started librarian.
            TacLibrarianTestSetup().tearDown()
            self.tearDownRoot()
            raise

    def tearDown(self):
        """Shut downs both librarian instances."""
        TacLibrarianTestSetup().tearDown()
        TacRestrictedLibrarianTestSetup().tearDown()
        self.tearDownRoot()

    def clear(self):
        """Clear all files from the Librarian"""
        cleanupLibrarianFiles()

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
    def logfile(self):
        return os.path.join(self.root, 'librarian.log')


class TacRestrictedLibrarianTestSetup(TacLibrarianTestSetup):
    """Fixture for the restricted librarian instance."""

    def setUp(self, spew=False):
        os.environ['RESTRICTED_LIBRARIAN'] = '1'
        try:
            super(TacRestrictedLibrarianTestSetup, self).setUp(spew)
        finally:
            del os.environ['RESTRICTED_LIBRARIAN']

    @property
    def pidfile(self):
        return os.path.join(self.root, 'restricted-librarian.pid')

    @property
    def logfile(self):
        return os.path.join(self.root, 'restricted-librarian.log')


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
