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
from canonical.launchpad.scripts.ftpmaster import (
    PackageLocationError, SoyuzScriptError)
from canonical.launchpad.scripts.create_rebuild import RebuildArchiveCreator
from canonical.testing import LaunchpadZopelessLayer


def get_spn(binary_package):
    """Return the SourcePackageName of the binary."""
    pub = binary_package.getCurrentPublication()
    return pub.sourcepackagerelease.sourcepackagename


class TestStartRebuildScript(unittest.TestCase):
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
        """Run start-rebuild.py, returning the result and output.

        Runs the wrapper script using Popen(), returns a tuple of the
        process's return code, stdout output and stderr output."""
        if extra_args is None:
            extra_args = []
        script = os.path.join(
            config.root, "scripts", "start-rebuild.py")
        args = [sys.executable, script, '-y']
        args.extend(extra_args)
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return (process.returncode, stdout, stderr)

    def getRebuildArchive(self, name):
        """Return rebuild archive with given name or None."""
        archives = [archive for archive in getUtility(IArchiveSet)
                    if archive.purpose == ArchivePurpose.REBUILD]

        # Return the archive if found, None otherwise.
        if len(archives) == 1:
            [result] = archives
        else:
            result = None

        return result

    def testRebuildArchiveCreation(self):
        """Start rebuild, check data before and after.

        Use the hoary-RELEASE suite along with the main component.
        """
        # Make sure a rebuild archive with the desired name does
        # not exist yet.
        self.assertTrue(
            self.getRebuildArchive(self.rebld_archive_name) is None)

        hoary = getUtility(IDistributionSet)['ubuntu']['hoary']

        # These source packages will be copied to the rebuild archive.
        hoary_sources = hoary.distribution.main_archive.getPublishedSources(
            distroseries=hoary, status=self.pending_statuses)

        src_names = sorted(source.displayname for source in hoary_sources)
        self.assertEqual(src_names, self.expected_src_names)

        # Command line arguments required for the invocation of the
        # 'start-rebuild.py' script.
        extra_args = [
            '-d', 'ubuntu', '-s', 'hoary', '-c', 'main', '-t',
            '"rebuild archive from %s"' % datetime.ctime(datetime.utcnow()),
            '-r', self.rebld_archive_name, '-u', 'salgado']

        # Start rebuild now!
        (return_code, out, err) = self.runWrapperScript(extra_args)

        # Check for zero exit code.
        self.assertEqual(return_code, 0)

        # Make sure the rebuild archive with the desired name was
        # created
        rebuild_archive = self.getRebuildArchive(self.rebld_archive_name)
        self.assertTrue(rebuild_archive is not None)

        # Make sure the source packages were cloned.
        rebuild_sources = rebuild_archive.getPublishedSources(
            distroseries=hoary, status=self.pending_statuses)

        rebuild_src_names = sorted(
            source.displayname for source in rebuild_sources)

        self.assertEqual(rebuild_src_names, self.expected_src_names)

        # Now check that we have build records for the sources cloned.
        builds = list(getUtility(IBuildSet).getBuildsForArchive(
            rebuild_archive, status=BuildStatus.NEEDSBUILD))

        # Please note: there will be no build for the pmount package
        # since it is architecture independent and the 'hoary'
        # DistroSeries in the sample data has no DistroArchSeries
        # with chroots set up.
        build_spns = [
            get_spn(removeSecurityProxy(build)).name for build in builds]

        self.assertEqual(build_spns, self.expected_build_spns)

    def assertRaisesWithContent(self, exception, exception_content,
                                func, *args):
        """Check if the given exception is raised with given content.

        If the expection isn't raised or the exception_content doesn't
        match what was raised an AssertionError is raised.
        """
        exception_name = str(exception).split('.')[-1]

        try:
            func(*args)
        except exception, err:
            if not str(err).startswith(exception_content):
                raise AssertionError(
                    "'%s' was not the reason expected" % str(err))
        else:
            raise AssertionError(
                "'%s' was not raised" % exception_name)

    def runScript(
        self, archive_name=None, component='main', suite='hoary',
        user='salgado', exists_before=False, exists_after=False,
        exception_type=None, exception_text=None, extra_args=None):
        """Run the script to test.

        :type archive_name: `str`
        :param archive_name: the name of the rebuild archive to create.
        :type component: `str`
        :param component: the name of the rebuild archive component.
        :type suite: `str`
        :param suite: the name of the rebuild archive suite.
        :type user: `str`
        :param user: the name of the user creating the archive.
        :type exists_before: `bool`
        :param exists_before: rebuild archive with given name should
            already exist if True.
        :type exists_after: `True`
        :param exists_after: the rebuild archive is expected to exist
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
        now = int(time.time())
        if archive_name is None:
            archive_name = "ra%s" % now

        rebuild_archive = self.getRebuildArchive(archive_name)
        if exists_before:
            self.assertTrue(rebuild_archive is not None)
        else:
            self.assertTrue(rebuild_archive is None)

        # Command line arguments required for the invocation of the
        # 'start-rebuild.py' script.
        script_args = [
            '-d', 'ubuntu', '-s', suite, '-c', component, '-t',
            '"rebuild archive from %s"' % datetime.ctime(datetime.utcnow()),
            '-r', archive_name, '-u', user]

        if extra_args is not None:
            script_args.extend(extra_args)

        script = RebuildArchiveCreator(
            'start-rebuild', dbuser=config.uploader.dbuser,
            test_args=script_args)

        if exception_type is not None:
            self.assertRaisesWithContent(
                exception_type, exception_text, script.mainTask)
        else:
            script.mainTask()

        rebuild_archive = self.getRebuildArchive(archive_name)
        if exists_after:
            self.assertTrue(rebuild_archive is not None)
        else:
            self.assertTrue(rebuild_archive is None)

        return rebuild_archive

    def testInvalidRebuildArchiveName(self):
        """Try rebuild with invalid archive name.

        The rebuild archive creation will fail with exit code 2.
        """
        now = int(time.time())
        # The colons in the name make it invalid.
        invalid_archive_name = "ra::%s" % now

        self.runScript(
            archive_name=invalid_archive_name,
            exception_type=SoyuzScriptError,
            exception_text="Invalid rebuild archive name")

    def testInvalidComponentName(self):
        """Try rebuild with invalid component name."""
        now = int(time.time())
        invalid_component = "component/:/%s" % now
        self.runScript(
            component=invalid_component,
            exception_type=SoyuzScriptError,
            exception_text="Invalid component name")

    def testInvalidSuite(self):
        """Try rebuild with invalid suite."""
        now = int(time.time())
        invalid_suite = "suite/:/%s" % now
        self.runScript(
            suite=invalid_suite,
            exception_type=PackageLocationError,
            exception_text="Could not find suite")

    def testInvalidUserName(self):
        """Try rebuild with invalid user name."""
        now = int(time.time())
        invalid_user = "user/:/%s" % now
        self.runScript(
            user=invalid_user,
            exception_type=SoyuzScriptError,
            exception_text="Invalid user name")

    def testXistingArchive(self):
        """Try rebuild with existing rebuild archive name.

        The rebuild archive creation will fail with exit code 5.
        """
        self.runScript(
            archive_name=self.rebld_archive_name, exists_before=True,
            exists_after=True, exception_type=SoyuzScriptError,
            exception_text="An archive rebuild named")

    def testArchWithoutBuilds(self):
        """Start rebuild with zero build for given architecture tag.

        Use the hoary-RELEASE suite along with the main component.
        """
        hoary = getUtility(IDistributionSet)['ubuntu']['hoary']

        # These source packages will be copied to the rebuild archive.
        hoary_sources = hoary.distribution.main_archive.getPublishedSources(
            distroseries=hoary, status=self.pending_statuses)

        src_names = sorted(source.displayname for source in hoary_sources)
        self.assertEqual(src_names, self.expected_src_names)

        # Restrict the builds to be created to the 'hppa' architecture
        # only. This should result in zero builds.
        extra_args = ['-a', 'hppa']
        rebuild_archive = self.runScript(
            extra_args=extra_args, exists_after=True)

        # Make sure the source packages were cloned.
        rebuild_sources = rebuild_archive.getPublishedSources(
            distroseries=hoary, status=self.pending_statuses)

        rebuild_src_names = sorted(
            source.displayname for source in rebuild_sources)

        self.assertEqual(rebuild_src_names, self.expected_src_names)

        # Now check that we have zero build records for the sources cloned.
        builds = list(getUtility(IBuildSet).getBuildsForArchive(
            rebuild_archive, status=BuildStatus.NEEDSBUILD))
        build_spns = [
            get_spn(removeSecurityProxy(build)).name for build in builds]

        self.assertTrue(len(build_spns) == 0)

    def testMultipleDistroArchSeriesSpecified(self):
        """Start rebuild with multiple architecture tags.

        Use the hoary-RELEASE suite along with the main component.
        """
        hoary = getUtility(IDistributionSet)['ubuntu']['hoary']

        # These source packages will be copied to the rebuild archive.
        hoary_sources = hoary.distribution.main_archive.getPublishedSources(
            distroseries=hoary, status=self.pending_statuses)

        src_names = sorted(source.displayname for source in hoary_sources)
        self.assertEqual(src_names, self.expected_src_names)

        # Please note:
        #   * the 'hppa' DistroArchSeries has no resulting builds.
        #   * the '-a' command line parameter is cumulative in nature
        #     i.e. the 'hppa' architecture tag specfied after the 'i386'
        #     tag does not overwrite the latter but is added to it.
        extra_args = ['-a', 'i386', '-a', 'hppa']
        rebuild_archive = self.runScript(
            extra_args=extra_args, exists_after=True)

        # Make sure the source packages were cloned.
        rebuild_sources = rebuild_archive.getPublishedSources(
            distroseries=hoary, status=self.pending_statuses)

        rebuild_src_names = sorted(
            source.displayname for source in rebuild_sources)
        self.assertEqual(rebuild_src_names, self.expected_src_names)

        # Now check that we have the build records expected.
        builds = list(getUtility(IBuildSet).getBuildsForArchive(
            rebuild_archive, status=BuildStatus.NEEDSBUILD))
        build_spns = [
            get_spn(removeSecurityProxy(build)).name for build in builds]
        self.assertEqual(build_spns, self.expected_build_spns)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
