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
    LayeredDocFileSuite, setUp as standard_setup)
from canonical.launchpad.interfaces import (
    DistroSeriesStatus, IDistributionSet)
from canonical.testing import LaunchpadZopelessLayer


def getUploadForSource(upload_path):
    """Return a NascentUpload object for bar 1.0-1 source."""
    policy = getPolicy(name='sync', distro='ubuntu', distroseries='hoary')
    return NascentUpload(datadir(upload_path), policy, mock_logger_quiet)


def getUploadForBinary(upload_path):
    """Return a NascentUpload object for binaries of bar 1:1.0-9 source."""
    policy = getPolicy(name='sync', distro='ubuntu', distroseries='hoary')
    policy.can_upload_binaries = True
    policy.can_upload_mixed = True
    return NascentUpload(datadir(upload_path), policy, mock_logger_quiet)


def testGlobalsSetup(test):
    """Inject useful helper functions in tests globals.

    We can use the getUpload* without unnecessary imports.
    """
    standard_setup(test)
    test.globs['getUploadForSource'] = getUploadForSource
    test.globs['getUploadForBinary'] = getUploadForBinary


def prepareHoaryForUploads(test):
    """Prepare ubuntu/hoary to receive uploads.

    Ensure ubuntu/hoary is ready to receive uploads in pocket
    RELEASE (DEVELOPMENT releasestate).
    """
    ubuntu = getUtility(IDistributionSet)['ubuntu']
    hoary = ubuntu['hoary']
    hoary.status = DistroSeriesStatus.DEVELOPMENT
    test.globs['ubuntu'] = ubuntu
    test.globs['hoary'] = hoary


def setUp(test):
    """Setup a typical nascentupload test environment.

    Use 'uploader' datebase user in a LaunchpadZopelessLayer transaction.
    Log in as a Launchpad admin (foo.bar@canonical.com).
    Setup test globals and prepare hoary for uploads
    """
    LaunchpadZopelessLayer.switchDbUser('uploader')
    login('foo.bar@canonical.com')
    testGlobalsSetup(test)
    prepareHoaryForUploads(test)


def tearDown(test):
    logout()


special = {
    'epoch-handling': LayeredDocFileSuite(
       'nascentupload-epoch-handling.txt', package=__name__,
       setUp=setUp, tearDown=tearDown, layer=LaunchpadZopelessLayer,
       optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS),

    'closing-bugs': LayeredDocFileSuite(
       'nascentupload-closing-bugs.txt', package=__name__,
       setUp=setUp, tearDown=tearDown, layer=LaunchpadZopelessLayer,
       optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS),

    'publishing-accepted-sources': LayeredDocFileSuite(
       'nascentupload-publishing-accepted-sources.txt', package=__name__,
       setUp=setUp, tearDown=tearDown, layer=LaunchpadZopelessLayer,
       optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS),
    }

def test_suite():
    suite = unittest.TestSuite()
    keys = special.keys()
    keys.sort()
    for key in keys:
        special_suite = special[key]
        suite.addTest(special_suite)
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
