# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import os
import subprocess
import sys
import time
import unittest

from datetime import datetime

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad.interfaces import (
    ArchivePurpose, BuildStatus, IArchiveSet, IBuildSet, IDistributionSet,
    PackagePublishingStatus)
from canonical.launchpad.interfaces.archivearch import IArchiveArchSet
from canonical.launchpad.scripts.ftpmaster import (
    PackageLocationError, SoyuzScriptError)
from canonical.launchpad.scripts.populate_archive import ArchivePopulator
from canonical.launchpad.scripts import QuietFakeLogger
from canonical.launchpad.tests.test_publishing import SoyuzTestPublisher
from canonical.launchpad.testing import TestCase
from canonical.testing import LaunchpadZopelessLayer
from canonical.testing.layers import DatabaseLayer


def get_spn(binary_package):
    """Return the SourcePackageName of the binary."""
    pub = binary_package.getCurrentPublication()
    return pub.sourcepackagerelease.sourcepackagename


class TestPopulateArchiveScript(TestCase):
    """Test the copy-package.py script."""

    layer = LaunchpadZopelessLayer
    rebld_archive_name = "ra%s" % int(time.time())
    expected_build_spns = [
        u'alsa-utils', u'cnews', u'evolution', u'libstdc++',
        u'linux-source-2.6.15', u'netapplet']
    expected_src_names = [
        u'alsa-utils 1.0.9a-4ubuntu1 in hoary',
        u'cnews cr.g7-37 in hoary', u'evolution 1.0 in hoary',
        u'libstdc++ b8p in hoary',
        u'linux-source-2.6.15 2.6.15.3 in hoary',
        u'netapplet 1.0-1 in hoary', u'pmount 0.1-2 in hoary']
    pending_statuses = (
        PackagePublishingStatus.PENDING,
        PackagePublishingStatus.PUBLISHED)

    def runWrapperScript(self, extra_args=None):
        """Run populate-archive.py, returning the result and output.

        Runs the wrapper script using Popen(), returns a tuple of the
        process's return code, stdout output and stderr output."""
        if extra_args is None:
            extra_args = []
        script = os.path.join(
            config.root, "scripts", "populate-archive.py")
        args = [sys.executable, script, '-y']
        args.extend(extra_args)
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return (process.returncode, stdout, stderr)

    def testCopyArchiveCreation(self):
        """Start archive population, check data before and after.

        Use the hoary-RELEASE suite along with the main component.
        """
        DatabaseLayer.force_dirty_database()
        # Make sure a copy archive with the desired name does
        # not exist yet.
        distro_name = 'ubuntu'
        name = self.rebld_archive_name
        distro = getUtility(IDistributionSet).getByName(distro_name)

        copy_archive = getUtility(IArchiveSet).getByDistroPurpose(
            distro, ArchivePurpose.COPY, name)
        # This is a sanity check: a copy archive with this name should not
        # exist yet.
        self.assertTrue(copy_archive is None)

        hoary = getUtility(IDistributionSet)[distro_name]['hoary']

        # Verify that we have the right source packages in the sample data.
        self._verifyPackagesInSampleData(hoary)

        # Command line arguments required for the invocation of the
        # 'populate-archive.py' script.
        extra_args = [
            '-a', 'x86',
            '--from-distribution', distro_name, '--from-suite', 'hoary',
            '--to-distribution', distro_name, '--to-suite', 'hoary',
            '--to-archive', name, '--to-user', 'salgado', '--reason',
            '"copy archive from %s"' % datetime.ctime(datetime.utcnow()),
            '--component', 'main'
            ]

        # Start archive population now!
        (return_code, out, err) = self.runWrapperScript(extra_args)

        # Check for zero exit code.
        self.assertEqual(
            return_code, 0, "=> %s\n=> %s\n=> %s\n" % (return_code, out, err))

        # Make sure the copy archive with the desired name was
        # created
        copy_archive = getUtility(IArchiveSet).getByDistroPurpose(
            distro, ArchivePurpose.COPY, name)
        self.assertTrue(copy_archive is not None)

        # Make sure the right source packages were cloned.
        self._verifyClonedSourcePackages(copy_archive, hoary)

        # Now check that we have build records for the sources cloned.
        builds = list(getUtility(IBuildSet).getBuildsForArchive(
            copy_archive, status=BuildStatus.NEEDSBUILD))

        # Please note: there will be no build for the pmount package
        # since it is architecture independent and the 'hoary'
        # DistroSeries in the sample data has no DistroArchSeries
        # with chroots set up.
        build_spns = [
            get_spn(removeSecurityProxy(build)).name for build in builds]

        self.assertEqual(build_spns, self.expected_build_spns)

        # Finally, we will test a repeated population of the same copy archive
        # and thus the merge copy mechanism.
        self._prepareMergeCopy()
        LaunchpadZopelessLayer.txn.commit()

        # Populate same copy archive again.
        (return_code, out, err) = self.runWrapperScript(extra_args)

        # Check for zero exit code.
        self.assertEqual(
            return_code, 0, "=> %s\n=> %s\n=> %s\n" % (return_code, out, err))
        # Make sure the right source packages were cloned.
        self._verifyClonedSourcePackages(
            copy_archive, hoary,
            # The set of packages that were superseded in the target archive.
            obsolete=set(['alsa-utils 1.0.9a-4ubuntu1 in hoary']),
            # The set of packages that are new/fresher in the source archive.
            new=set(['alsa-utils 2.0 in hoary',
                     'new-in-second-round 1.0 in hoary'])
            )

    def _prepareMergeCopy(self):
        test_publisher = SoyuzTestPublisher()
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        hoary = ubuntu.getSeries('hoary')
        test_publisher.addFakeChroots(hoary)
        unused = test_publisher.setUpDefaultDistroSeries(hoary)
        new_package = test_publisher.getPubSource(
            sourcename="new-in-second-round", version="1.0",
            distroseries=hoary, archive=ubuntu.main_archive)
        fresher_package = test_publisher.getPubSource(
            sourcename="alsa-utils", version="2.0", distroseries=hoary,
            archive=ubuntu.main_archive)

    def runScript(
        self, archive_name=None, suite='hoary',
        user='salgado', exists_before=False, exists_after=False,
        exception_type=None, exception_text=None, extra_args=None):
        """Run the script to test.

        :type archive_name: `str`
        :param archive_name: the name of the copy archive to create.
        :type suite: `str`
        :param suite: the name of the copy archive suite.
        :type user: `str`
        :param user: the name of the user creating the archive.
        :type exists_before: `bool`
        :param exists_before: copy archive with given name should
            already exist if True.
        :type exists_after: `True`
        :param exists_after: the copy archive is expected to exist
            after script invocation if True.
        :type exception_type: type
        :param exception_type: the type of exception expected in case
            of failure.
        :type exception_text: `str`
        :param exception_text: expected exception text prefix in case
            of failure.
        :type extra_args: list of strings
        :param extra_args: additional arguments to be passed to the
            script (if any).
        """
        class FakeZopeTransactionManager:
            def commit(self):
                pass
            def begin(self):
                pass

        now = int(time.time())
        if archive_name is None:
            archive_name = "ra%s" % now

        distro_name = 'ubuntu'
        distro = getUtility(IDistributionSet).getByName(distro_name)

        copy_archive = getUtility(IArchiveSet).getByDistroPurpose(
            distro, ArchivePurpose.COPY, archive_name)

        if exists_before:
            self.assertTrue(copy_archive is not None)
        else:
            self.assertTrue(copy_archive is None)

        # Command line arguments required for the invocation of the
        # 'populate-archive.py' script.
        script_args = [
            '--from-distribution', distro_name,
            '--to-distribution', distro_name, '--to-suite', suite,
            '--to-archive', archive_name, '--to-user', user, '--reason',
            '"copy archive from %s"' % datetime.ctime(datetime.utcnow())
            ]

        if extra_args is not None:
            script_args.extend(extra_args)

        script = ArchivePopulator(
            'populate-archive', dbuser=config.uploader.dbuser,
            test_args=script_args)

        script.logger = QuietFakeLogger()
        script.txn = FakeZopeTransactionManager()

        if exception_type is not None:
            self.assertRaisesWithContent(
                exception_type, exception_text, script.mainTask)
        else:
            script.mainTask()

        copy_archive = getUtility(IArchiveSet).getByDistroPurpose(
            distro, ArchivePurpose.COPY, archive_name)

        if exists_after:
            self.assertTrue(copy_archive is not None)
        else:
            self.assertTrue(copy_archive is None)

        return copy_archive

    def testInvalidCopyArchiveName(self):
        """Try copy archive creation/population with an invalid archive name.

        When trying to create and populate a copy archive with an invalid name
        the script should fail with an appropriate error message.
        """
        now = int(time.time())
        # The colons in the name make it invalid.
        invalid_archive_name = "ra//%s" % now

        extra_args = ['-a', 'x86']
        self.runScript(
            extra_args=extra_args,
            archive_name=invalid_archive_name,
            exception_type=SoyuzScriptError,
            exception_text=(
                "Invalid archive name: '%s'" % invalid_archive_name))

    def testInvalidSuite(self):
        """Try copy archive creation/population with a non-existent suite.

        A suite is a combination of a distro series and pocket e.g.
        hoary-updates or hardy-security.
        In the case where a non-existent suite is specified the script should
        abort with an appropriate error message.
        """
        now = int(time.time())
        invalid_suite = "suite/:/%s" % now
        extra_args = ['-a', 'x86']
        self.runScript(
            extra_args=extra_args,
            suite=invalid_suite,
            exception_type=PackageLocationError,
            exception_text="Could not find suite '%s'" % invalid_suite)

    def testInvalidUserName(self):
        """Try copy archive population with an invalid user name.

        The destination/copy archive will be created for some Launchpad user.
        If the user name passed is invalid the script should abort with an
        appropriate error message.
        """
        now = int(time.time())
        invalid_user = "user//%s" % now
        extra_args = ['-a', 'x86']
        self.runScript(
            extra_args=extra_args,
            user=invalid_user,
            exception_type=SoyuzScriptError,
            exception_text="Invalid user name: '%s'" % invalid_user)

    def testArchWithoutBuilds(self):
        """Try copy archive population with no builds.

        The user may specify a number of given architecture tags on the
        command line.
        The script should create build records only for the specified
        architecture tags that are supported by the destination distro series.

        In this (test) case the specified architecture tag should have the
        effect that no build records are created.
        """
        hoary = getUtility(IDistributionSet)['ubuntu']['hoary']

        # Verify that we have the right source packages in the sample data.
        self._verifyPackagesInSampleData(hoary)

        # Restrict the builds to be created to the 'hppa' architecture
        # only. This should result in zero builds.
        extra_args = ['-a', 'hppa']
        copy_archive = self.runScript(
            extra_args=extra_args, exists_after=True)

        # Make sure the right source packages were cloned.
        self._verifyClonedSourcePackages(copy_archive, hoary)

        # Now check that we have zero build records for the sources cloned.
        builds = list(getUtility(IBuildSet).getBuildsForArchive(
            copy_archive, status=BuildStatus.NEEDSBUILD))
        build_spns = [
            get_spn(removeSecurityProxy(build)).name for build in builds]

        self.assertTrue(len(build_spns) == 0)

    def testInvalidProcessorFamilyName(self):
        """Try copy archive population with an invalid processor family name.

        This test should provoke a `SoyuzScriptError` exception.
        """
        extra_args = ['-a', 'wintel']
        copy_archive = self.runScript(
            extra_args=extra_args,
            exception_type=SoyuzScriptError,
            exception_text="Invalid processor family: 'wintel'")

    def testMissingProcessorFamily(self):
        """Try copy archive population without a sngle processor family name.

        This test should provoke a `SoyuzScriptError` exception.
        """
        copy_archive = self.runScript(
            exception_type=SoyuzScriptError,
            exception_text="error: processor families not specified.")

    def testMultipleDistroArchSeriesSpecified(self):
        """Try copy archive population with multiple architecture tags.

        The user may specify a number of given architecture tags on the
        command line.
        The script should create build records only for the specified
        architecture tags that are supported by the destination distro series.

        In this (test) case the script should create the build records for the
        'i386' architecture.
        """
        hoary = getUtility(IDistributionSet)['ubuntu']['hoary']

        # Verify that we have the right source packages in the sample data.
        self._verifyPackagesInSampleData(hoary)

        # Please note:
        #   * the 'hppa' DistroArchSeries has no resulting builds.
        #   * the '-a' command line parameter is cumulative in nature
        #     i.e. the 'hppa' architecture tag specified after the 'i386'
        #     tag does not overwrite the latter but is added to it.
        extra_args = ['-a', 'x86', '-a', 'hppa']
        copy_archive = self.runScript(
            extra_args=extra_args, exists_after=True)

        # Make sure the right source packages were cloned.
        self._verifyClonedSourcePackages(copy_archive, hoary)

        # Now check that we have the build records expected.
        builds = list(getUtility(IBuildSet).getBuildsForArchive(
            copy_archive, status=BuildStatus.NEEDSBUILD))
        build_spns = [
            get_spn(removeSecurityProxy(build)).name for build in builds]
        self.assertEqual(build_spns, self.expected_build_spns)

        def get_family_names(result_set):
            """Extract processor family names from result set."""
            family_names = []
            for archivearch in rset:
                family_names.append(
                    removeSecurityProxy(archivearch).processorfamily.name)
            return family_names

        # Make sure that the processor family names specified for the copy
        # archive at hand were stored in the database.
        rset = getUtility(IArchiveArchSet).getByArchive(copy_archive)
        self.assertEqual(get_family_names(rset), [u'x86', u'hppa'])


    def _verifyClonedSourcePackages(
        self, copy_archive, series, obsolete=None, new=None):
        """Verify that the expected source packages have been cloned.

        The destination copy archive should be populated with the expected
        source packages.

        :type copy_archive: `Archive`
        :param copy_archive: the destination copy archive to check.
        :type series: `DistroSeries`
        :param series: the destination distro series.
        """
        # Make sure the source packages were cloned.
        target_set = set(self.expected_src_names)
        copy_sources = copy_archive.getPublishedSources(
            distroseries=series, status=self.pending_statuses)
        copy_src_names = set(
            source.displayname for source in copy_sources)
        if obsolete is not None:
            target_set -= obsolete
        if new is not None:
            target_set = target_set.union(new)
        self.assertEqual(copy_src_names, target_set)

    def _verifyPackagesInSampleData(self, series):
        """Verify that the expected source packages are in the sample data.

        :type series: `DistroSeries`
        :param series: the origin distro series.
        """
        # These source packages will be copied to the copy archive.
        sources = series.distribution.main_archive.getPublishedSources(
            distroseries=series, status=self.pending_statuses)

        src_names = sorted(source.displayname for source in sources)
        # Make sure the source to be copied are the ones we expect (this
        # should break in case of a sample data change/corruption).
        self.assertEqual(src_names, self.expected_src_names)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
