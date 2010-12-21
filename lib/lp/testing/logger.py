# Copyright 2009, 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Frequently-used logging utilities for test suite."""

__metaclass__ = type
__all__ = [
    'MockLogger',
    ]

import logging
import sys

# XXX cprov 20071018: This class should be combined with
# launchpad.scripts.logger.FakeLogger at some point.

class MockLogger:
    """Imitates a logger, but prints to standard output."""
    loglevel = logging.INFO

    def __init__(self, outfile=None):
        if outfile is None:
            outfile = sys.stdout
        self.outfile = outfile

    def setLevel(self, loglevel):
        self.loglevel = loglevel

    def getEffectiveLevel(self):
        return self.loglevel

    def log(self, msg, *args, **kwargs):
        # The standard logger takes a template string as the first
        # argument, but we must only attempt to use it as one if we have
        # arguments. Otherwise logging of messages with string formatting
        # sequences will die.
        if len(args) > 0:
            msg %= args

        self.outfile.write("log> %s\n" % msg)

        if "exc_info" in kwargs:
            import sys
            import traceback
            exception = traceback.format_exception(*sys.exc_info())
            for item in exception:
                for line in item.splitlines():
                    self.log(line)

    def debug(self, *args, **kwargs):
        if self.loglevel <= logging.DEBUG:
            self.log(*args, **kwargs)

    def info(self, *args, **kwargs):
        if self.loglevel <= logging.INFO:
            self.log(*args, **kwargs)

    def warn(self, *args, **kwargs):
        if self.loglevel <= logging.WARN:
            self.log(*args, **kwargs)

    def error(self, *args, **kwargs):
        if self.loglevel <= logging.ERROR:
            self.log(*args, **kwargs)

    def exception(self, *args):
        self.log(*args, **{'exc_info': True})
