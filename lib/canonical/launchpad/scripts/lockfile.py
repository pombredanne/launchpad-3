# LockFile class stolen from arch-pqm by Carlos Perello Marin
#
# Copyright (c) 2003,2004 Colin Walters <walters@verbum.org>
# Copyright (c)  2004 Canonical Ltd.
#       Author: Robert Collins <robertc@robertcollins.net>
# Copyright (c) 2003 Walter Landry

import datetime
import logging
import os
import sys

from stat import ST_CTIME

class LockFile(object):
    """I represent a lock that is made on the file system,
    to prevent concurrent execution of this code"""

    def __init__(self, filename, timeout=None, logger=None):
        """Create a new instance of LockFile.

        filename is the file to be used as the lock.
        timeout is a datetime.timedelta object with an time span while the
        lock is valid. If it's None we took it as a day.
        logger is a logging object where we could log anything we need if it's
        not None.
        """

        self.filename=filename
        self.locked=False
        self.logger=logger
        if timeout is None:
            # By default, the lock can only be one day old.
            self.delta = datetime.timedelta(days=1)
        else:
            self.delta = timeout

    def acquire(self):
        """Get the lock of self.filename.

        Remove the lock if it already exists and it's older than self.delta.
        If it's newer, raise an OSError exception.
        """

        if self.logger:
            self.logger.info('creating lockfile')
        try:
            os.open(self.filename, os.O_CREAT | os.O_EXCL)
            self.locked=True
        except OSError, e:
            # The lock file already exists.
            # Check if it's still valid.
            lock_time = datetime.datetime.fromtimestamp(
                os.stat(self.filename)[ST_CTIME])
            current_time = datetime.datetime.today()
            if lock_time < (current_time - self.delta):
                # The lock file is older than self.delta, it should be
                # removed.
                os.unlink(self.filename)

                if self.logger:
                    self.logger.warning('Removing stalled lockfile')

                # and recreate it as usual.
                os.open(self.filename, os.O_CREAT | os.O_EXCL)
                self.locked=True
            else:
                raise OSError, e

    def release(self):
        """Release the lock on self.filename."""
        if not self.locked:
            return
        if self.logger:
            self.logger.debug('Removing lock file: %s', self.filename)
        os.unlink(self.filename)
        self.locked=False

