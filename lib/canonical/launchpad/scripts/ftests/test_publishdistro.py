# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Functional tests for publish-distro.py script."""

__metaclass__ = type

import os
import subprocess
import sys
import unittest

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces import (
    IArchiveSet, IPersonSet)
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

        self.assertEqual(0, rc, "Publisher failed with:\n%s\n%s" % (out, err))
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

        self.assertEqual(0, rc, "Publisher failed with:\n%s\n%s" % (out, err))

        self.assertEqual(pub_source.status, PackagePublishingStatus.PENDING)
        self.assertEqual(pub_source2.status, PackagePublishingStatus.PUBLISHED)

        foo_path = "%s/main/f/foo/foo.dsc" % self.pool_dir
        self.assertEqual(False, os.path.exists(foo_path))

        baz_path = "%s/main/b/baz/baz.dsc" % self.pool_dir
        self.assertEqual('baz', open(baz_path).read().strip())

    def testForPPA(self):
        """Try to run publish-distro in PPA mode.

        It should deal only with PPA publications.
        """
        pub_source = self.getPubSource(filecontent='foo')

        cprov_ppa = getUtility(IArchiveSet).new(
            name='default', owner=getUtility(IPersonSet).getByName('cprov'))
        pub_source2 = self.getPubSource(
            sourcename='baz', filecontent='baz', archive=cprov_ppa)

        name16_ppa = getUtility(IArchiveSet).new(
            name='default', owner=getUtility(IPersonSet).getByName('name16'))
        pub_source3 = self.getPubSource(
            sourcename='bar', filecontent='bar', archive=name16_ppa)

        self.layer.txn.commit()

        rc, out, err = self.runPublishDistro(['--ppa'])

        self.assertEqual(0, rc, "Publisher failed with:\n%s\n%s" % (out, err))

        self.assertEqual(pub_source.status, PackagePublishingStatus.PENDING)
        self.assertEqual(pub_source2.status, PackagePublishingStatus.PUBLISHED)
        self.assertEqual(pub_source3.status, PackagePublishingStatus.PUBLISHED)

        foo_path = "%s/main/f/foo/foo.dsc" % self.pool_dir
        self.assertEqual(False, os.path.exists(foo_path))

        baz_path = os.path.join(
            config.personalpackagearchive.root, 'cprov/default',
            'ubuntutest/pool/main/b/baz/baz.dsc')
        self.assertEqual('baz', open(baz_path).read().strip())

        bar_path = os.path.join(
            config.personalpackagearchive.root, 'name16/default',
            'ubuntutest/pool/main/b/bar/bar.dsc')
        self.assertEqual('bar', open(bar_path).read().strip())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
