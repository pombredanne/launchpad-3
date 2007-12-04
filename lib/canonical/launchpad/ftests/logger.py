# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Frequently-used logging utilities for test suite."""

__metaclass__ = type
__all__ = ['MockLogger']

import logging

# XXX cprov 20071018: This class should be combined with
# launchpad.scripts.logger.FakeLogger at some point.

class MockLogger:
    """Imitates a logger, but prints to standard output.
    """
    loglevel = logging.INFO

    def setLevel(self, loglevel):
        self.loglevel = loglevel

    def getEffectiveLevel(self):
        return self.loglevel

    def log(self, *args, **kwargs):
        print "log>", ' '.join(args)

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

