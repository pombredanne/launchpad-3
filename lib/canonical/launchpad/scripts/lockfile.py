# LockFile class stolen from arch-pqm by Carlos Perello Marin
#
# Copyright (c) 2003,2004 Colin Walters <walters@verbum.org>
# Copyright (c)  2004 Canonical Ltd.
#       Author: Robert Collins <robertc@robertcollins.net>
# Copyright (c) 2003 Walter Landry

import logging, os, sys

class LockFile(object):
    """I represent a lock that is made on the file system,
    to prevent concurrent execution of this code"""
    def __init__(self, filename, logger=None):
        self.filename=filename
        self.locked=False
        self.logger=logger

    def acquire(self):
        if self.logger:
            self.logger.info('creating lockfile')
        try:
            os.open(self.filename, os.O_CREAT | os.O_EXCL)
            self.locked=True
        except OSError, e:
            if self.logger:
                self.logger.info("lockfile %s already exists, exiting",
                    self.filename)
            sys.exit(0)

    def release(self):
        if not self.locked:
            return
        if self.logger:
            self.logger.debug('Removing lock file: %s', self.filename)
        os.unlink(self.filename)
        self.locked=False

