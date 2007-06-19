# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Runs the nascentupload-epoch-handling.txt test."""

__metaclass__ = type

import unittest

from zope.component import getUtility
from zope.testing import doctest

from canonical.archiveuploader.nascentupload import NascentUpload
from canonical.archiveuploader.tests import (
    datadir, getPolicy, mock_logger_quiet)
from canonical.launchpad.ftests import login, logout
from canonical.launchpad.ftests.test_system_documentation import (
    LayeredDocFileSuite)
from canonical.launchpad.interfaces import IDistributionSet
from canonical.lp.dbschema import DistroSeriesStatus
from canonical.testing import LaunchpadZopelessLayer


def getUploadBarSourceNoEpoch():
    """Return a NascentUpload object for bar 1.0-1 source."""
    policy = getPolicy(name='sync', distro='ubuntu', distroseries='hoary')
    return NascentUpload(
        datadir('suite/bar_1.0-1/bar_1.0-1_source.changes'),
        policy, mock_logger_quiet)

def getUploadBarSourceEpoch():
    """Return a NascentUpload object for bar 1:1.0-1 source."""
    policy = getPolicy(name='sync', distro='ubuntu', distroseries='hoary')
    return NascentUpload(
        datadir('suite/bar_1.0-1_epoched/bar_1.0-1_source.changes'),
        policy, mock_logger_quiet)

def getUploadBarSourceForBinary():
    """Return a NascentUpload object for bar 1:1.0-9 source."""
    policy = getPolicy(name='sync', distro='ubuntu', distroseries='hoary')
    return NascentUpload(
        datadir('suite/bar_1.0-9/bar_1.0-9_source.changes'),
        policy, mock_logger_quiet)

def getUploadBarBinary():
    """Return a NascentUpload object for binaries of bar 1:1.0-9 source."""
    policy = getPolicy(name='sync', distro='ubuntu', distroseries='hoary')
    policy.can_upload_binaries = True
    policy.can_upload_mixed = True
    return NascentUpload(
        datadir('suite/bar_1.0-9_binary/bar_1.0-9_i386.changes'),
        policy, mock_logger_quiet)

def setUp(test):
    """Setup a typical nascentupload test environment.

    Use 'uploader' datebase user in a LaunchpadZopelessLayer transaction.

    Log in as a Launchpad admin (foo.bar@canonical.com).

    Include this module invironment in the test environment, so it can use
    the getUpload* helper functions.

    Finally, ensure ubuntu/hoary is ready to receive uploads in pocket
    RELEASE (DEVELOPMENT releasestate).
    """
    LaunchpadZopelessLayer.switchDbUser('uploader')
    login('foo.bar@canonical.com')
    test.globs.update(globals())

    ubuntu = getUtility(IDistributionSet)['ubuntu']
    hoary = ubuntu['hoary']
    hoary.status = DistroSeriesStatus.DEVELOPMENT

def tearDown(test):
    logout()

def test_suite():
    suite = LayeredDocFileSuite(
        '../../archiveuploader/ftests/nascentupload-epoch-handling.txt',
        setUp=setUp, tearDown=tearDown,
        layer=LaunchpadZopelessLayer,
        optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS)
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
