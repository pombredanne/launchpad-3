# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Functional tests for publish-distro.py script."""

__metaclass__ = type

from optparse import OptionParser
import os
import shutil
import subprocess
import sys
import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad.scripts.logger import QuietFakeLogger
from canonical.launchpad.interfaces import (
    ArchivePurpose, IArchiveSet, IDistributionSet, IPersonSet,
    PackagePublishingStatus)
from canonical.launchpad.scripts import publishdistro
from canonical.launchpad.scripts.base import LaunchpadScriptFailure
from canonical.launchpad.tests.test_publishing import TestNativePublishingBase

class TestPublishDistro(TestNativePublishingBase):
    """Test the publish-distro.py script works properly."""

    def runPublishDistro(self, extra_args=None, distribution="ubuntutest"):
        """Run publish-distro without invoking the script.

        This method hooks into the publishdistro module to run the
        publish-distro script without the overhead of using Popen.
        """
        args = ["-d", distribution]
        if extra_args is not None:
            args.extend(extra_args)
        parser = OptionParser()
        publishdistro.add_options(parser)
        options, args = parser.parse_args(args=args)
        self.layer.switchDbUser(config.archivepublisher.dbuser)
        result = publishdistro.run_publisher(options, self.layer.txn,
                                             log=QuietFakeLogger())
        self.layer.switchDbUser('launchpad')

    def runPublishDistroScript(self):
        """Run publish-distro.py, returning the result and output."""
        script = os.path.join(config.root, "scripts", "publish-distro.py")
        args = [sys.executable, script, "-v", "-d", "ubuntutest"]
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return (process.returncode, stdout, stderr)

    def testPublishDistroRun(self):
        """Try a simple publish-distro run.

        Expect database publishing record to be updated to PUBLISHED and
        the file to be written in disk.

        This method also ensures the publish-distro.py script is runnable.
        """
        pub_source = self.getPubSource(filecontent='foo')
        self.layer.txn.commit()

        rc, out, err = self.runPublishDistroScript()

        pub_source.sync()
        self.assertEqual(0, rc, "Publisher failed with:\n%s\n%s" % (out, err))
        self.assertEqual(pub_source.status, PackagePublishingStatus.PUBLISHED)

        foo_path = "%s/main/f/foo/foo.dsc" % self.pool_dir
        self.assertEqual(open(foo_path).read().strip(), 'foo')

    def testDirtyPocketProcessing(self):
        """Test dirty pocket processing.

        Make a DELETED source to see if the dirty pocket processing
        works for deletions.
        """
        pub_source = self.getPubSource(filecontent='foo')
        self.layer.txn.commit()
        self.runPublishDistro()
        pub_source.sync()

        random_person = getUtility(IPersonSet).getByName('name16')
        pub_source.requestDeletion(random_person)
        self.layer.txn.commit()
        self.assertTrue(pub_source.scheduleddeletiondate is None,
            "pub_source.scheduleddeletiondate should not be set, and it is.")
        self.runPublishDistro()
        pub_source.sync()
        self.assertTrue(pub_source.scheduleddeletiondate is not None,
            "pub_source.scheduleddeletiondate should be set, and it's not.")

    def assertExists(self, path):
        """Assert if the given path exists."""
        self.assertTrue(os.path.exists(path), "Not Found: '%s'" % path)

    def assertNotExists(self, path):
        """Assert if the given path does not exist."""
        self.assertFalse(os.path.exists(path), "Found: '%s'" % path)

    def testRunWithSuite(self):
        """Try to run publish-distro with restricted suite option.

        Expect only update and disk writing only in the publishing record
        targeted to the specified suite, other records should be untouched
        and not present in disk.
        """
        pub_source = self.getPubSource(filecontent='foo')
        pub_source2 = self.getPubSource(
            sourcename='baz', filecontent='baz',
            distroseries=self.ubuntutest['hoary-test'])
        self.layer.txn.commit()

        self.runPublishDistro(['-s', 'hoary-test'])

        pub_source.sync()
        pub_source2.sync()
        self.assertEqual(pub_source.status, PackagePublishingStatus.PENDING)
        self.assertEqual(
            pub_source2.status, PackagePublishingStatus.PUBLISHED)

        foo_path = "%s/main/f/foo/foo.dsc" % self.pool_dir
        self.assertNotExists(foo_path)

        baz_path = "%s/main/b/baz/baz.dsc" % self.pool_dir
        self.assertEqual('baz', open(baz_path).read().strip())

    def publishToArchiveWithOverriddenDistsroot(self, archive):
        """Publish a test package to the specified archive.

        Publishes a test package but overrides the distsroot.
        :return: A tuple of the path to the overridden distsroot and the
                 configured distsroot, in that order.
        """
        self.getPubSource(filecontent="flangetrousers", archive=archive)
        self.layer.txn.commit()
        pubconf = removeSecurityProxy(archive.getPubConfig())
        tmp_path = "/tmp/tmpdistroot"
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        os.mkdir(tmp_path)
        myargs = ['-R', tmp_path]
        if archive.purpose == ArchivePurpose.PARTNER:
            myargs.append('--partner')
        self.runPublishDistro(myargs)
        return tmp_path, pubconf.distsroot

    def testDistsrootOverridePrimaryArchive(self):
        """Test the -R option to publish-distro.

        Make sure that -R works with the primary archive.
        """
        main_archive = getUtility(IDistributionSet)['ubuntutest'].main_archive
        tmp_path, distsroot = self.publishToArchiveWithOverriddenDistsroot(
            main_archive)
        distroseries = 'breezy-autotest'
        self.assertExists(os.path.join(tmp_path, distroseries, 'Release'))
        self.assertNotExists(
            os.path.join("%s" % distsroot, distroseries, 'Release'))
        shutil.rmtree(tmp_path)

    def testDistsrootOverridePartnerArchive(self):
        """Test the -R option to publish-distro.

        Make sure the -R option affects the partner archive.
        """
        # XXX cprov 20071201: Disabling this test temporarily while we are
        # publishing partner archive with apt-ftparchive as a quick solution
        # for bug #172275. Once bug #172308 (adding extra field in packages
        # tables) is fixed we can switch back to NoMoreAptFtparchive and
        # re-enable this test.
        return
        ubuntu = getUtility(IDistributionSet)['ubuntutest']
        partner_archive = ubuntu.getArchiveByComponent('partner')
        tmp_path, distsroot = self.publishToArchiveWithOverriddenDistsroot(
            partner_archive)
        distroseries = 'breezy-autotest'
        self.assertExists(os.path.join(tmp_path, distroseries, 'Release'))
        self.assertNotExists(
            os.path.join("%s" % distsroot, distroseries, 'Release'))
        shutil.rmtree(tmp_path)

    def testForPPA(self):
        """Try to run publish-distro in PPA mode.

        It should deal only with PPA publications.
        """
        pub_source = self.getPubSource(filecontent='foo')

        cprov = getUtility(IPersonSet).getByName('cprov')
        pub_source2 = self.getPubSource(
            sourcename='baz', filecontent='baz', archive=cprov.archive)

        ubuntutest = getUtility(IDistributionSet)['ubuntutest']
        name16 = getUtility(IPersonSet).getByName('name16')
        getUtility(IArchiveSet).new(purpose=ArchivePurpose.PPA, owner=name16,
            distribution=ubuntutest)
        pub_source3 = self.getPubSource(
            sourcename='bar', filecontent='bar', archive=name16.archive)

        # Override PPAs distributions
        naked_archive = removeSecurityProxy(cprov.archive)
        naked_archive.distribution = self.ubuntutest
        naked_archive = removeSecurityProxy(name16.archive)
        naked_archive.distribution = self.ubuntutest

        self.layer.txn.commit()

        self.runPublishDistro(['--ppa'])

        pub_source.sync()
        pub_source2.sync()
        pub_source3.sync()
        self.assertEqual(pub_source.status, PackagePublishingStatus.PENDING)
        self.assertEqual(
            pub_source2.status, PackagePublishingStatus.PUBLISHED)
        self.assertEqual(
            pub_source3.status, PackagePublishingStatus.PUBLISHED)

        foo_path = "%s/main/f/foo/foo.dsc" % self.pool_dir
        self.assertEqual(False, os.path.exists(foo_path))

        baz_path = os.path.join(
            config.personalpackagearchive.root, cprov.name,
            'ubuntutest/pool/main/b/baz/baz.dsc')
        self.assertEqual('baz', open(baz_path).read().strip())

        bar_path = os.path.join(
            config.personalpackagearchive.root, name16.name,
            'ubuntutest/pool/main/b/bar/bar.dsc')
        self.assertEqual('bar', open(bar_path).read().strip())

    def testForPrivatePPA(self):
        """Run publish-distro in private PPA mode.

        It should only publish private PPAs.
        """
        # First, we'll make cprov's archive private.
        ubuntutest = getUtility(IDistributionSet)['ubuntutest']
        cprov = getUtility(IPersonSet).getByName('cprov')
        cprov_ppa = removeSecurityProxy(cprov.archive)
        cprov_ppa.private = True
        cprov_ppa.buildd_secret = "secret"
        cprov_ppa.distribution = self.ubuntutest

        # Publish something to cprov's PPA:
        pub_source =  self.getPubSource(
            sourcename='baz', filecontent='baz', archive=cprov.archive)
        self.layer.txn.commit()

        # Try a plain PPA run, to ensure the private one is NOT published.
        self.runPublishDistro(['--ppa'])

        pub_source.sync()
        self.assertEqual(pub_source.status, PackagePublishingStatus.PENDING)

        # Now publish the private PPAs and make sure they are really
        # published.
        self.runPublishDistro(['--private-ppa'])

        pub_source.sync()
        self.assertEqual(pub_source.status, PackagePublishingStatus.PUBLISHED)

    def testRunWithEmptySuites(self):
        """Try a publish-distro run on empty suites in careful_apt mode

        Expect it to create all indexes, including current 'Release' file
        for the empty suites specified.
        """
        self.runPublishDistro(
            ['-A', '-s', 'hoary-test-updates', '-s', 'hoary-test-backports'])

        # Check "Release" files
        release_path = "%s/hoary-test-updates/Release" % self.config.distsroot
        self.assertExists(release_path)

        release_path = (
            "%s/hoary-test-backports/Release" % self.config.distsroot)
        self.assertExists(release_path)

        release_path = "%s/hoary-test/Release" % self.config.distsroot
        self.assertNotExists(release_path)

        # Check some index files
        index_path = (
            "%s/hoary-test-updates/main/binary-i386/Packages"
            % self.config.distsroot)
        self.assertExists(index_path)

        index_path = (
            "%s/hoary-test-backports/main/binary-i386/Packages"
            % self.config.distsroot)
        self.assertExists(index_path)

        index_path = (
            "%s/hoary-test/main/binary-i386/Packages" % self.config.distsroot)
        self.assertNotExists(index_path)

    def testExclusiveOptions(self):
        """Test that some command line options are mutually exclusive."""
        self.assertRaises(
            LaunchpadScriptFailure,
            self.runPublishDistro, ['--ppa', '--partner'])
        self.assertRaises(
            LaunchpadScriptFailure,
            self.runPublishDistro, ['--ppa', '--private-ppa'])
        self.assertRaises(
            LaunchpadScriptFailure,
            self.runPublishDistro, ['--partner', '--private-ppa'])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
