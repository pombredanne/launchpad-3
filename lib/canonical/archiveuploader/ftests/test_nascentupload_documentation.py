# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Runs the nascentupload-epoch-handling.txt test."""

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.archiveuploader.nascentupload import NascentUpload
from canonical.archiveuploader.tests import (
    datadir, getPolicy, mock_logger_quiet)
from canonical.launchpad.database import (
    ComponentSelection, LibraryFileAlias)
from canonical.launchpad.ftests import login, logout
from canonical.launchpad.interfaces import (
    DistroSeriesStatus, IComponentSet, IDistributionSet)
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setGlobs)
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
    setGlobs(test)
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
    # Hoary needs to allow uploads for universe.
    universe = getUtility(IComponentSet)['universe']
    ComponentSelection(distroseries=hoary, component=universe)
    # Create a fake hoary/i386 chroot.
    fake_chroot = LibraryFileAlias.get(1)
    hoary['i386'].addOrUpdateChroot(fake_chroot)

    LaunchpadZopelessLayer.txn.commit()


def setUp(test):
    """Setup a typical nascentupload test environment.

    Use 'uploader' datebase user in a LaunchpadZopelessLayer transaction.
    Log in as a Launchpad admin (foo.bar@canonical.com).
    Setup test globals and prepare hoary for uploads
    """
    login('foo.bar@canonical.com')
    testGlobalsSetup(test)
    prepareHoaryForUploads(test)
    LaunchpadZopelessLayer.switchDbUser('uploader')


def tearDown(test):
    logout()


def test_suite():
    return LayeredDocFileSuite(
       'nascentupload-closing-bugs.txt',
       'nascentupload-epoch-handling.txt',
       'nascentupload-publishing-accepted-sources.txt',
       setUp=setUp, tearDown=tearDown, layer=LaunchpadZopelessLayer)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
