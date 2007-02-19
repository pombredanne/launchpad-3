# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: 28075773-73fd-4699-82ed-610df135d2a5

__metaclass__ = type

__all__ = ['datadir', 'mock_options', 'mock_logger', 'mock_logger_quiet']

import os

here = os.path.dirname(os.path.realpath(__file__))

def datadir(path):
    """Return fully-qualified path inside the test data directory."""
    if path.startswith("/"):
        raise ValueError("Path is not relative: %s" % path)
    return os.path.join(here, 'data', path)


class MockUploadOptions:
    """Mock upload policy options helper"""

    def __init__(self, distro='ubuntutest', distrorelease=None):
        self.distro = distro
        self.distrorelease = distrorelease


class MockUploadLogger:
    """Mock upload logger facility helper"""

    def __init__(self, verbose=True):
        self.verbose = verbose

    def debug(self, s):
        if self.verbose is not True:
            return
        print 'DEBUG:', s

    def info(self, s):
        print 'INFO:', s

    def warn(self, s):
        print 'WARN:', s

    def error(self, s):
        print 'ERROR:', s


mock_options = MockUploadOptions()

mock_logger = MockUploadLogger()

mock_logger_quiet = MockUploadLogger(verbose=False)
