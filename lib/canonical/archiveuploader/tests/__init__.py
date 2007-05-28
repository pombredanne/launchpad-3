# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['datadir', 'getPolicy', 'mock_options', 'mock_logger',
           'mock_logger_quiet']

import os

from canonical.archiveuploader.uploadpolicy import findPolicyByName


here = os.path.dirname(os.path.realpath(__file__))


def datadir(path):
    """Return fully-qualified path inside the test data directory."""
    if path.startswith("/"):
        raise ValueError("Path is not relative: %s" % path)
    return os.path.join(here, 'data', path)


class MockUploadOptions:
    """Mock upload policy options helper"""

    def __init__(self, distro='ubuntutest', distroseries=None, buildid=None):
        self.distro = distro
        self.distroseries = distroseries
        self.buildid = buildid

def getPolicy(name='anything', distro='ubuntu', distroseries=None,
              buildid=None):
    """Build and return an Upload Policy for the given context."""
    policy = findPolicyByName(name)
    options = MockUploadOptions(distro, distroseries, buildid)
    policy.setOptions(options)
    return policy


class MockUploadLogger:
    """Mock upload logger facility helper"""

    def __init__(self, verbose=True):
        self.verbose = verbose

    def debug(self, message, **kw):
        if self.verbose is not True:
            return
        print 'DEBUG:', message

    def info(self, message, **kw):
        print 'INFO:', message

    def warn(self, message, **kw):
        print 'WARN:', message

    def error(self, message, **kw):
        print 'ERROR:', message


mock_options = MockUploadOptions()
mock_logger = MockUploadLogger()
mock_logger_quiet = MockUploadLogger(verbose=False)
