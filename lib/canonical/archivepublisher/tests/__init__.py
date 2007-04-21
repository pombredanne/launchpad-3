# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: 28075773-73fd-4699-82ed-610df135d2a5

__metaclass__ = type

__all__ = ['datadir', 'getPolicy', 'mock_options', 'mock_logger',
           'mock_logger_quiet']

import os

from canonical.archivepublisher.uploadpolicy import findPolicyByName


here = os.path.dirname(os.path.realpath(__file__))


def datadir(path):
    """Return fully-qualified path inside the test data directory."""
    if path.startswith("/"):
        raise ValueError("Path is not relative: %s" % path)
    return os.path.join(here, 'data', path)


class MockUploadOptions:
    """Mock upload policy options helper"""

    def __init__(self, distro='ubuntutest', distrorelease=None, buildid=None):
        self.distro = distro
        self.distrorelease = distrorelease
        self.buildid = buildid


def getPolicy(name='anything', distro='ubuntu', distrorelease=None,
              buildid=None):
    """Build and return an Upload Policy for the given context."""
    policy = findPolicyByName(name)
    options = MockUploadOptions(distro, distrorelease, buildid)
    policy.setOptions(options)
    return policy


class MockUploadLogger:
    """Mock upload logger facility helper"""

    def __init__(self, verbose=True):
        self.verbose = verbose

    def debug(self, message):
        if self.verbose is not True:
            return
        print 'DEBUG:', message

    def info(self, message):
        print 'INFO:', message

    def warn(self, message):
        print 'WARN:', message

    def error(self, message):
        print 'ERROR:', message


mock_options = MockUploadOptions()
mock_logger = MockUploadLogger()
mock_logger_quiet = MockUploadLogger(verbose=False)
