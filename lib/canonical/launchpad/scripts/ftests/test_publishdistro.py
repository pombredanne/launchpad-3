# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Functional tests for publish-distro.py script."""

__metaclass__ = type

import os
import subprocess
import sys
import unittest

from canonical.config import config
from canonical.launchpad.tests.test_publishing import TestNativePublishingBase
from canonical.lp.dbschema import (
    PackagePublishingStatus, PackagePublishingPocket)

class TestPublishDistro(TestNativePublishingBase):
    """Test the publish-distro.py script works properly."""

    def runPublishDistro(self, extra_args, distribution="ubuntutest"):
        """Run publish-distro.py, returning the result and output."""
        script = os.path.join(config.root, "scripts", "publish-distro.py")
        args = [sys.executable, script, "-v", "-d", "ubuntutest"]
        args.extend(extra_args)
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return (process.returncode, stdout, stderr)

    def testRun(self):
        """Try a simple publish-distro run.

        Expect database publishing record to be updated to PUBLISHED and
        the file to be written in disk.
        """
        pub_source = self.getPubSource(filecontent='foo')
        self.layer.txn.commit()

        rc, out, err = self.runPublishDistro([])

        self.assertEqual(0, rc)
        self.assertEqual(pub_source.status, PackagePublishingStatus.PUBLISHED)

        foo_path = "%s/main/f/foo/foo.dsc" % self.pool_dir
        self.assertEqual(open(foo_path).read().strip(), 'foo')

    def testRunWithSuite(self):
        """Try to run publish-distro with restricted suite option.

        Expect only update and disk writing only in the publishing record
        targeted to the specified suite, other records should be untouched
        and not present in disk.
        """
        pub_source = self.getPubSource(filecontent='foo')
        pub_source2 = self.getPubSource(
            sourcename='baz', filecontent='baz',
            distrorelease=self.ubuntutest['hoary-test'])
        self.layer.txn.commit()

        rc, out, err = self.runPublishDistro(['-s', 'hoary-test'])

        self.assertEqual(0, rc)

        self.assertEqual(pub_source.status, PackagePublishingStatus.PENDING)
        self.assertEqual(pub_source2.status, PackagePublishingStatus.PUBLISHED)

        foo_path = "%s/main/f/foo/foo.dsc" % self.pool_dir
        self.assertEqual(False, os.path.exists(foo_path))

        baz_path = "%s/main/b/baz/baz.dsc" % self.pool_dir
        self.assertEqual('baz', open(baz_path).read().strip())

    def testRunWithEmptySuites(self):
        """Try a publish-distro run on empty suites in careful_apt mode

        Expect it to create all indexes, including current 'Release' file
        for the empty suites specified.
        """
        rc, out, err = self.runPublishDistro(
            ['-A', '-s', 'hoary-test-updates', '-s', 'hoary-test-backports'])

        self.assertEqual(0, rc)

        # Check "Release" files
        release_path = "%s/hoary-test-updates/Release" % self.config.distsroot
        self.assertTrue(os.path.exists(release_path))

        release_path = "%s/hoary-test-backports/Release" % self.config.distsroot
        self.assertTrue(os.path.exists(release_path))

        release_path = "%s/hoary-test/Release" % self.config.distsroot
        self.assertFalse(os.path.exists(release_path))

        # Check some index files
        index_path = (
            "%s/hoary-test-updates/main/binary-i386/Packages"
            % self.config.distsroot)
        self.assertTrue(os.path.exists(index_path))

        index_path = (
            "%s/hoary-test-backports/main/binary-i386/Packages"
            % self.config.distsroot)
        self.assertTrue(os.path.exists(index_path))

        index_path = (
            "%s/hoary-test/main/binary-i386/Packages" % self.config.distsroot)
        self.assertFalse(os.path.exists(index_path))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
