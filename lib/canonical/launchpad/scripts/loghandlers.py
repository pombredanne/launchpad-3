# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Backport of Python 2.6 logging handlers.

Do not import this module directly, instead import from
`canonical.launchpad.scripts`.

Given that most of the contents of this file are derived from the Python 2.6
distribution, the above license statement is probably wrong.
"""

# Comments starting with 'BACKPORT' have been added to indicate changes from
# the original.

__metaclass__ = type
__all__ = [
    'WatchedFileHandler',
    ]

import codecs
import logging
import os
from stat import (
    ST_DEV,
    ST_INO,
    )


class WatchedFileHandler(logging.FileHandler):
    """
    A handler for logging to a file, which watches the file
    to see if it has changed while in use. This can happen because of
    usage of programs such as newsyslog and logrotate which perform
    log file rotation. This handler, intended for use under Unix,
    watches the file to see if it has changed since the last emit.
    (A file has changed if its device or inode have changed.)
    If it has changed, the old file stream is closed, and the file
    opened to get a new stream.

    This handler is not appropriate for use under Windows, because
    under Windows open files cannot be moved or renamed - logging
    opens the files with exclusive locks - and so there is no need
    for such a handler. Furthermore, ST_INO is not supported under
    Windows; stat always returns zero for this value.

    This handler is based on a suggestion and patch by Chad J.
    Schroeder.
    """
    def __init__(self, filename, mode='a', encoding=None):
        # BACKPORT: The 'delay' parameter has been removed, since Python 2.4
        # logging doesn't have the delay feature.
        logging.FileHandler.__init__(self, filename, mode, encoding)
        # BACKPORT: In Python 2.6, the constructor stores the encoding
        # parameter. Here we save it so we can use it in the _open method.
        self.encoding = encoding
        if not os.path.exists(self.baseFilename):
            self.dev, self.ino = -1, -1
        else:
            stat = os.stat(self.baseFilename)
            self.dev, self.ino = stat[ST_DEV], stat[ST_INO]

    def _open(self):
        """
        Open the current base file with the (original) mode and encoding.
        Return the resulting stream.
        """
        # BACKPORT: Copied from the 2.6 implementation so that emit() can call
        # it. In the Python 2.6 version, this is also called by the
        # constructor.
        if self.encoding is None:
            stream = open(self.baseFilename, self.mode)
        else:
            stream = codecs.open(self.baseFilename, self.mode, self.encoding)
        return stream

    def emit(self, record):
        """
        Emit a record.

        First check if the underlying file has changed, and if it
        has, close the old stream and reopen the file to get the
        current stream.
        """
        if not os.path.exists(self.baseFilename):
            stat = None
            changed = 1
        else:
            # BACKPORT: Doing a stat on every log seems unwise. A signal
            # handling log handler might be better.
            stat = os.stat(self.baseFilename)
            changed = (stat[ST_DEV] != self.dev) or (stat[ST_INO] != self.ino)
        if changed and self.stream is not None:
            self.stream.flush()
            self.stream.close()
            self.stream = self._open()
            if stat is None:
                stat = os.stat(self.baseFilename)
            self.dev, self.ino = stat[ST_DEV], stat[ST_INO]
        logging.FileHandler.emit(self, record)
