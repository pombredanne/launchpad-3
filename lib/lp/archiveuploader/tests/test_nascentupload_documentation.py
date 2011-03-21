# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Runs the doctests for archiveuploader module."""

__metaclass__ = type

import os
import unittest

from zope.component import getUtility

from canonical.launchpad.database.librarian import LibraryFileAlias
from canonical.launchpad.ftests import (
    import_public_test_keys,
    login,
    logout,
    )
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite,
    setGlobs,
    )
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.archiveuploader.nascentupload import NascentUpload
from lp.archiveuploader.tests import (
    datadir,
    getPolicy,
    )
from lp.archiveuploader.uploadpolicy import ArchiveUploadType
from lp.registry.interfaces.distribution import IDistributionSet
from lp.services.log.logger import DevNullLogger
from lp.soyuz.model.component import ComponentSelection
from lp.soyuz.interfaces.component import IComponentSet


def getUploadForSource(upload_path):
    """Return a NascentUpload object for a source."""
    policy = getPolicy(name='sync', distro='ubuntu', distroseries='hoary')
    return NascentUpload.from_changesfile_path(
        datadir(upload_path), policy, DevNullLogger())


def getPPAUploadForSource(upload_path, ppa):
    """Return a NascentUpload object for a PPA source."""
    policy = getPolicy(name='insecure', distro='ubuntu', distroseries='hoary')
    policy.archive = ppa
    return NascentUpload.from_changesfile_path(
        datadir(upload_path), policy, DevNullLogger())


def getUploadForBinary(upload_path):
    """Return a NascentUpload object for binaries."""
    policy = getPolicy(name='sync', distro='ubuntu', distroseries='hoary')
    policy.accepted_type = ArchiveUploadType.BINARY_ONLY
    return NascentUpload.from_changesfile_path(
        datadir(upload_path), policy, DevNullLogger())


def testGlobalsSetup(test):
    """Inject useful helper functions in tests globals.

    We can use the getUpload* without unnecessary imports.
    """
    import_public_test_keys()
    setGlobs(test)
    test.globs['getUploadForSource'] = getUploadForSource
    test.globs['getUploadForBinary'] = getUploadForBinary
    test.globs['getPPAUploadForSource'] = getPPAUploadForSource


def prepareHoaryForUploads(test):
    """Prepare ubuntu/hoary to receive uploads.

    Ensure ubuntu/hoary is ready to receive and build new uploads in
    the RELEASE pocket (they are auto-overridden to the 'universe'
    component).
    """
    ubuntu = getUtility(IDistributionSet)['ubuntu']
    hoary = ubuntu['hoary']

    # Allow uploads to the universe component.
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
    suite = unittest.TestSuite()
    tests_dir = os.path.dirname(os.path.realpath(__file__))

    filenames = [
        filename
        for filename in os.listdir(tests_dir)
        if filename.lower().endswith('.txt')
        ]

    for filename in sorted(filenames):
        test = LayeredDocFileSuite(
            filename, setUp=setUp, tearDown=tearDown,
            layer=LaunchpadZopelessLayer)
        suite.addTest(test)

    return suite
