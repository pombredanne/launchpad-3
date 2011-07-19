# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Functional tests for publish-distro.py script."""

__metaclass__ = type

from optparse import OptionValueError
import os
import shutil
import subprocess
import sys
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.testing.layers import ZopelessDatabaseLayer
from lp.archivepublisher.config import getPubConfig
from lp.archivepublisher.interfaces.publisherconfig import IPublisherConfigSet
from lp.archivepublisher.publishing import Publisher
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.log.logger import (
    BufferLogger,
    DevNullLogger,
    )
from lp.services.scripts.base import LaunchpadScriptFailure
from lp.soyuz.enums import (
    ArchivePurpose,
    BinaryPackageFormat,
    PackagePublishingStatus,
    )
from lp.soyuz.interfaces.archive import IArchiveSet
from lp.soyuz.scripts.publishdistro import PublishDistro
from lp.soyuz.tests.test_publishing import TestNativePublishingBase
from lp.testing import TestCaseWithFactory
from lp.testing.fakemethod import FakeMethod
from lp.testing.faketransaction import FakeTransaction


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
        publish_distro = PublishDistro(test_args=args)
        publish_distro.logger = BufferLogger()
        publish_distro.txn = self.layer.txn
        self.layer.switchDbUser(config.archivepublisher.dbuser)
        publish_distro.main()
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

        foo_path = "%s/main/f/foo/foo_666.dsc" % self.pool_dir
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

        foo_path = "%s/main/f/foo/foo_666.dsc" % self.pool_dir
        self.assertNotExists(foo_path)

        baz_path = "%s/main/b/baz/baz_666.dsc" % self.pool_dir
        self.assertEqual('baz', open(baz_path).read().strip())

    def publishToArchiveWithOverriddenDistsroot(self, archive):
        """Publish a test package to the specified archive.

        Publishes a test package but overrides the distsroot.
        :return: A tuple of the path to the overridden distsroot and the
                 configured distsroot, in that order.
        """
        self.getPubSource(filecontent="flangetrousers", archive=archive)
        self.layer.txn.commit()
        pubconf = getPubConfig(archive)
        tmp_path = os.path.join(pubconf.archiveroot, "tmpdistroot")
        if os.path.exists(tmp_path):
            shutil.rmtree(tmp_path)
        os.makedirs(tmp_path)
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

        foo_path = "%s/main/f/foo/foo_666.dsc" % self.pool_dir
        self.assertEqual(False, os.path.exists(foo_path))

        baz_path = os.path.join(
            config.personalpackagearchive.root, cprov.name,
            'ppa/ubuntutest/pool/main/b/baz/baz_666.dsc')
        self.assertEqual('baz', open(baz_path).read().strip())

        bar_path = os.path.join(
            config.personalpackagearchive.root, name16.name,
            'ppa/ubuntutest/pool/main/b/bar/bar_666.dsc')
        self.assertEqual('bar', open(bar_path).read().strip())

    def testForPrivatePPA(self):
        """Run publish-distro in private PPA mode.

        It should only publish private PPAs.
        """
        # First, we'll make a private PPA and populate it with a
        # publishing record.
        ubuntutest = getUtility(IDistributionSet)['ubuntutest']
        private_ppa = self.factory.makeArchive(
            private=True, distribution=ubuntutest)

        # Publish something to the private PPA:
        pub_source = self.getPubSource(
            sourcename='baz', filecontent='baz', archive=private_ppa)
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

    def testPublishPrimaryDebug(self):
        # 'ubuntutest' (default testing distribution) has no DEBUG
        # archive, Thus an error is raised.
        self.assertRaises(
            OptionValueError,
            self.runPublishDistro, ['--primary-debug'])

        # The DEBUG repository path was not created.
        ubuntutest = getUtility(IDistributionSet)['ubuntutest']
        root_dir = getUtility(
            IPublisherConfigSet).getByDistribution(ubuntutest).root_dir
        repo_path = os.path.join(
            root_dir, 'ubuntutest-debug')
        self.assertNotExists(repo_path)

        # We will create the DEBUG archive for ubuntutest, so it can
        # be published.
        debug_archive = getUtility(IArchiveSet).new(
            purpose=ArchivePurpose.DEBUG, owner=ubuntutest.owner,
            distribution=ubuntutest)

        # We will also create a source & binary pair of pending
        # publications. Only the DDEB (binary) will be moved to
        # the DEBUG archive, exactly as it would happen in normal
        # operation, see nascentupload-ddebs.txt.
        self.prepareBreezyAutotest()
        pub_binaries = self.getPubBinaries(format=BinaryPackageFormat.DDEB)
        for binary in pub_binaries:
            binary.archive = debug_archive

        # Commit setup changes, so the script can operate on them.
        self.layer.txn.commit()

        # After publication, the DDEB is published and indexed.
        self.runPublishDistro(['--primary-debug'])

        debug_pool_path = os.path.join(repo_path, 'pool/main/f/foo')
        self.assertEqual(
            os.listdir(debug_pool_path), ['foo-bin_666_all.ddeb'])

        debug_index_path = os.path.join(
            repo_path, 'dists/breezy-autotest/main/binary-i386/Packages')
        self.assertEqual(
            open(debug_index_path).readlines()[0], 'Package: foo-bin\n')

    def testPublishCopyArchive(self):
        """Run publish-distro in copy archive mode.

        It should only publish copy archives.
        """
        ubuntutest = getUtility(IDistributionSet)['ubuntutest']
        cprov = getUtility(IPersonSet).getByName('cprov')
        copy_archive_name = 'test-copy-publish'

        # The COPY repository path is not created yet.
        root_dir = getUtility(
            IPublisherConfigSet).getByDistribution(ubuntutest).root_dir
        repo_path = os.path.join(
            root_dir,
            ubuntutest.name + '-' + copy_archive_name,
            ubuntutest.name)
        self.assertNotExists(repo_path)

        copy_archive = getUtility(IArchiveSet).new(
            distribution=ubuntutest, owner=cprov, name=copy_archive_name,
            purpose=ArchivePurpose.COPY, enabled=True)
        # Save some test CPU cycles by avoiding logging in as the user
        # necessary to alter the publish flag.
        removeSecurityProxy(copy_archive).publish = True

        # Publish something.
        pub_source = self.getPubSource(
            sourcename='baz', filecontent='baz', archive=copy_archive)

        # Try a plain PPA run, to ensure the copy archive is not published.
        self.runPublishDistro(['--ppa'])

        self.assertEqual(pub_source.status, PackagePublishingStatus.PENDING)

        # Now publish the copy archives and make sure they are really
        # published.
        self.runPublishDistro(['--copy-archive'])

        self.assertEqual(pub_source.status, PackagePublishingStatus.PUBLISHED)

        # Make sure that the files were published in the right place.
        pool_path = os.path.join(repo_path, 'pool/main/b/baz/baz_666.dsc')
        self.assertExists(pool_path)

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


class FakeArchive:
    def __init__(self, purpose=ArchivePurpose.PRIMARY):
        self.purpose = purpose


class FakePublisher:
    """A very simple fake `Publisher`."""
    def __init__(self):
        self.A_publish = FakeMethod()
        self.A2_markPocketsWithDeletionsDirty = FakeMethod()
        self.B_dominate = FakeMethod()
        self.C_doFTPArchive = FakeMethod()
        self.C_writeIndexes = FakeMethod()
        self.D_writeReleaseFiles = FakeMethod()


class TestPublishDistroMethods(TestCaseWithFactory):
    """Fine-grained unit tests for `PublishDistro`."""

    layer = ZopelessDatabaseLayer

    def makeScript(self, distribution=None, args=[]):
        """Create a `PublishDistro` for `distribution`."""
        if distribution is None:
            distribution = self.factory.makeDistribution()
        full_args = ['-d', distribution.name] + args
        script = PublishDistro(test_args=full_args)
        script.distribution = distribution
        script.logger = DevNullLogger()
        return script

    def test_isCareful_is_false_if_option_not_set(self):
        self.assertFalse(self.makeScript().isCareful(False))

    def test_isCareful_is_true_if_option_is_set(self):
        self.assertTrue(self.makeScript().isCareful(True))

    def test_isCareful_is_true_if_global_careful_option_is_set(self):
        self.assertTrue(self.makeScript(args=['--careful']).isCareful(False))

    def test_describeCare_reports_non_careful_option(self):
        self.assertEqual("Normal", self.makeScript().describeCare(False))

    def test_describeCare_reports_careful_option(self):
        self.assertEqual("Careful", self.makeScript().describeCare(True))

    def test_describeCare_reports_careful_override(self):
        self.assertEqual(
            "Careful (Overridden)",
            self.makeScript(args=['--careful']).describeCare(False))

    def test_countExclusiveOptions_is_zero_if_none_set(self):
        self.assertEqual(0, self.makeScript().countExclusiveOptions())

    def test_countExclusiveOptions_counts_partner(self):
        self.assertEqual(
            1, self.makeScript(args=['--partner']).countExclusiveOptions())

    def test_countExclusiveOptions_counts_ppa(self):
        self.assertEqual(
            1, self.makeScript(args=['--ppa']).countExclusiveOptions())

    def test_countExclusiveOptions_counts_private_ppa(self):
        self.assertEqual(
            1,
            self.makeScript(args=['--private-ppa']).countExclusiveOptions())

    def test_countExclusiveOptions_counts_primary_debug(self):
        self.assertEqual(
            1,
            self.makeScript(args=['--primary-debug']).countExclusiveOptions())

    def test_countExclusiveOptions_counts_copy_archive(self):
        self.assertEqual(
            1,
            self.makeScript(args=['--copy-archive']).countExclusiveOptions())

    def test_countExclusiveOptions_detects_conflict(self):
        script = self.makeScript(args=['--ppa', '--partner'])
        self.assertEqual(2, script.countExclusiveOptions())

    def test_validateOptions_rejects_nonoption_arguments(self):
        script = self.makeScript(args=['please'])
        self.assertRaises(OptionValueError, script.validateOptions)

    def test_validateOptions_rejects_exclusive_option_conflict(self):
        # If more than one of the exclusive options are set,
        # validateOptions raises that as an error.
        script = self.makeScript()
        script.countExclusiveOptions = FakeMethod(2)
        self.assertRaises(OptionValueError, script.validateOptions)

    def test_validateOptions_does_not_accept_distsroot_for_ppa(self):
        script = self.makeScript(args=['--ppa', '--distsroot=/tmp'])
        self.assertRaises(OptionValueError, script.validateOptions)

    def test_validateOptions_does_not_accept_distsroot_for_private_ppa(self):
        script = self.makeScript(args=['--private-ppa', '--distsroot=/tmp'])
        self.assertRaises(OptionValueError, script.validateOptions)

    def test_findDistro_finds_distribution(self):
        distro = self.factory.makeDistribution()
        self.assertEqual(distro, self.makeScript(distro).findDistro())

    def test_findDistro_raises_if_distro_not_found(self):
        wrong_name = self.factory.getUniqueString()
        self.assertRaises(
            OptionValueError,
            PublishDistro(test_args=['-d', wrong_name]).findDistro)

    def test_findSuite_finds_release_pocket(self):
        series = self.factory.makeDistroSeries()
        distro = series.distribution
        self.assertEqual(
            (series.name, PackagePublishingPocket.RELEASE),
            self.makeScript(distro).findSuite(series.name))

    def test_findSuite_finds_other_pocket(self):
        series = self.factory.makeDistroSeries()
        distro = series.distribution
        self.assertEqual(
            (series.name, PackagePublishingPocket.UPDATES),
            self.makeScript(distro).findSuite(series.name + "-updates"))

    def test_findSuite_raises_if_not_found(self):
        self.assertRaises(
            OptionValueError,
            self.makeScript().findSuite, self.factory.getUniqueString())

    def test_findAllowedSuites_finds_nothing_if_no_suites_given(self):
        self.assertContentEqual([], self.makeScript().findAllowedSuites())

    def test_findAllowedSuites_finds_series_and_pocket(self):
        series = self.factory.makeDistroSeries()
        suite = "%s-updates" % series.name
        script = self.makeScript(series.distribution, ['--suite', suite])
        self.assertContentEqual(
            [(series.name, PackagePublishingPocket.UPDATES)],
            script.findAllowedSuites())

    def test_findAllowedSuites_finds_multiple(self):
        series = self.factory.makeDistroSeries()
        script = self.makeScript(series.distribution, [
            '--suite', '%s-updates' % series.name,
            '--suite', series.name])
        expected_suites = [
            (series.name, PackagePublishingPocket.UPDATES),
            (series.name, PackagePublishingPocket.RELEASE),
            ]
        self.assertContentEqual(expected_suites, script.findAllowedSuites())

    def test_getDebugArchive_returns_list(self):
        distro = self.factory.makeDistribution()
        script = self.makeScript(distro)
        debug_archive = self.factory.makeArchive(
            distro, purpose=ArchivePurpose.DEBUG)
        self.assertEqual([debug_archive], script.getDebugArchive())

    def test_getDebugArchive_raises_if_not_found(self):
        self.assertRaises(OptionValueError, self.makeScript().getDebugArchive)

    def test_getDebugArchive_ignores_other_archive_purposes(self):
        distro = self.factory.makeDistribution()
        script = self.makeScript(distro)
        self.factory.makeArchive(distro, purpose=ArchivePurpose.PARTNER)
        self.assertRaises(OptionValueError, script.getDebugArchive)

    def test_getDebugArchive_ignores_other_distros(self):
        self.factory.makeArchive(purpose=ArchivePurpose.DEBUG)
        self.assertRaises(OptionValueError, self.makeScript().getDebugArchive)

    def test_getCopyArchives_returns_list(self):
        distro = self.factory.makeDistribution()
        script = self.makeScript(distro)
        copy_archive = self.factory.makeArchive(
            distro, purpose=ArchivePurpose.COPY)
        self.assertEqual([copy_archive], script.getCopyArchives())

    def test_getCopyArchives_raises_if_not_found(self):
        self.assertRaises(
            LaunchpadScriptFailure, self.makeScript().getCopyArchives)

    def test_getCopyArchives_ignores_other_archive_purposes(self):
        distro = self.factory.makeDistribution()
        script = self.makeScript(distro)
        self.factory.makeArchive(distro, purpose=ArchivePurpose.PARTNER)
        self.assertRaises(LaunchpadScriptFailure, script.getCopyArchives)

    def test_getCopyArchives_ignores_other_distros(self):
        self.factory.makeArchive(purpose=ArchivePurpose.COPY)
        self.assertRaises(
            LaunchpadScriptFailure, self.makeScript().getCopyArchives)

    def test_getPPAs_gets_pending_distro_PPAs_if_careful(self):
        distro = self.factory.makeDistribution()
        script = self.makeScript(distro, ['--careful'])
        ppa = self.factory.makeArchive(distro, purpose=ArchivePurpose.PPA)
        self.factory.makeSourcePackagePublishingHistory(archive=ppa)
        self.assertContentEqual([ppa], script.getPPAs())

    def test_getPPAs_gets_nonpending_distro_PPAs_if_careful(self):
        distro = self.factory.makeDistribution()
        script = self.makeScript(distro, ['--careful'])
        ppa = self.factory.makeArchive(distro, purpose=ArchivePurpose.PPA)
        self.assertContentEqual([ppa], script.getPPAs())

    def test_getPPAs_gets_pending_distro_PPAs_if_not_careful(self):
        distro = self.factory.makeDistribution()
        script = self.makeScript(distro)
        ppa = self.factory.makeArchive(distro, purpose=ArchivePurpose.PPA)
        self.factory.makeSourcePackagePublishingHistory(archive=ppa)
        self.assertContentEqual([ppa], script.getPPAs())

    def test_getPPAs_ignores_nonpending_distro_PPAs_if_not_careful(self):
        distro = self.factory.makeDistribution()
        script = self.makeScript(distro)
        self.factory.makeArchive(distro, purpose=ArchivePurpose.PPA)
        self.assertContentEqual([], script.getPPAs())

    def test_getPPAs_returns_empty_if_careful_and_no_PPAs_found(self):
        self.assertContentEqual(
            [], self.makeScript(args=['--careful']).getPPAs())

    def test_getPPAs_returns_empty_if_not_careful_and_no_PPAs_found(self):
        self.assertContentEqual([], self.makeScript().getPPAs())

    def test_getTargetArchives_gets_partner_archive(self):
        distro = self.factory.makeDistribution()
        partner = self.factory.makeArchive(
            distro, purpose=ArchivePurpose.PARTNER)
        script = self.makeScript(distro, ['--partner'])
        self.assertContentEqual([partner], script.getTargetArchives())

    def test_getTargetArchives_ignores_public_ppas_if_private(self):
        distro = self.factory.makeDistribution()
        self.factory.makeArchive(
            distro, purpose=ArchivePurpose.PPA, private=False)
        script = self.makeScript(distro, ['--private-ppa'])
        self.assertContentEqual([], script.getTargetArchives())

    def test_getTargetArchives_gets_private_ppas_if_private(self):
        distro = self.factory.makeDistribution()
        ppa = self.factory.makeArchive(
            distro, purpose=ArchivePurpose.PPA, private=True)
        script = self.makeScript(distro, ['--private-ppa', '--careful'])
        self.assertContentEqual([ppa], script.getTargetArchives())

    def test_getTargetArchives_gets_public_ppas_if_not_private(self):
        distro = self.factory.makeDistribution()
        ppa = self.factory.makeArchive(
            distro, purpose=ArchivePurpose.PPA, private=False)
        script = self.makeScript(distro, ['--ppa', '--careful'])
        self.assertContentEqual([ppa], script.getTargetArchives())

    def test_getTargetArchives_ignores_private_ppas_if_not_private(self):
        distro = self.factory.makeDistribution()
        self.factory.makeArchive(
            distro, purpose=ArchivePurpose.PPA, private=True)
        script = self.makeScript(distro, ['--ppa'])
        self.assertContentEqual([], script.getTargetArchives())

    def test_getTargetArchives_gets_primary_debug_archive(self):
        distro = self.factory.makeDistribution()
        debug = self.factory.makeArchive(distro, purpose=ArchivePurpose.DEBUG)
        script = self.makeScript(distro, ['--primary-debug'])
        self.assertContentEqual([debug], script.getTargetArchives())

    def test_getTargetArchives_gets_copy_archives(self):
        distro = self.factory.makeDistribution()
        copy = self.factory.makeArchive(distro, purpose=ArchivePurpose.COPY)
        script = self.makeScript(distro, ['--copy-archive'])
        self.assertContentEqual([copy], script.getTargetArchives())

    def test_getPublisher_returns_publisher(self):
        distro = self.factory.makeDistribution()
        script = self.makeScript(distro)
        publisher = script.getPublisher(distro.main_archive, None)
        self.assertIsInstance(publisher, Publisher)

    def test_deleteArchive_deletes_ppa(self):
        distro = self.factory.makeDistribution()
        ppa = self.factory.makeArchive(distro, purpose=ArchivePurpose.PPA)
        script = self.makeScript(distro)
        deletion_done = script.deleteArchive(
            ppa, script.getPublisher(ppa, []))
        self.assertTrue(deletion_done)
        self.assertContentEqual([], script.getPPAs())

    def test_deleteArchive_ignores_non_ppa(self):
        distro = self.factory.makeDistribution()
        archive = self.factory.makeArchive(
            distro, purpose=ArchivePurpose.DEBUG)
        script = self.makeScript(distro)
        deletion_done = script.deleteArchive(archive, None)
        self.assertFalse(deletion_done)
        self.assertContentEqual([archive], script.getDebugArchive())

    def test_publishArchive_drives_publisher(self):
        distro = self.factory.makeDistribution()
        script = self.makeScript(distro)
        script.txn = FakeTransaction()
        publisher = FakePublisher()
        script.publishArchive(FakeArchive(), publisher)
        self.assertEqual(1, publisher.A_publish.call_count)
        self.assertEqual(
            1, publisher.A2_markPocketsWithDeletionsDirty.call_count)
        self.assertEqual(1, publisher.B_dominate.call_count)
        self.assertEqual(1, publisher.D_writeReleaseFiles.call_count)

    def test_publishArchive_uses_apt_ftparchive_for_main_archive(self):
        distro = self.factory.makeDistribution()
        script = self.makeScript(distro)
        script.txn = FakeTransaction()
        publisher = FakePublisher()
        script.publishArchive(FakeArchive(), publisher)
        self.assertEqual(1, publisher.C_doFTPArchive.call_count)
        self.assertEqual(0, publisher.C_writeIndexes.call_count)

    def test_publishArchive_writes_own_indexes_for_ppa(self):
        distro = self.factory.makeDistribution()
        script = self.makeScript(distro)
        script.txn = FakeTransaction()
        publisher = FakePublisher()
        script.publishArchive(FakeArchive(ArchivePurpose.PPA), publisher)
        self.assertEqual(0, publisher.C_doFTPArchive.call_count)
        self.assertEqual(1, publisher.C_writeIndexes.call_count)
