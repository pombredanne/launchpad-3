# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Frequently-used logging utilities for test suite."""

__metaclass__ = type
__all__ = ['MockLogger']

# XXX cprov 20071018: This class should be combined with with
# launchpad.scripts.logger.FakeLogger at some point.

class MockLogger:
    """Imitates a logger, but prints to standard output."""

    def log(self, *args, **kwargs):
        print "log>", ' '.join(args)

        if "exc_info" in kwargs:
            import sys
            import traceback
            exception = traceback.format_exception(*sys.exc_info())
            for item in exception:
                for line in item.splitlines():
                    self.log(line)

    debug = info = warn = error = log

    def exception(self, *args):
        self.log(*args, **{'exc_info': True})

