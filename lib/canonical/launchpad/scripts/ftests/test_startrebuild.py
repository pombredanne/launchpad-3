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
    ArchivePurpose, BuildStatus, IArchiveSet, IBuildSet, IDistroSeriesSet,
    PackagePublishingStatus)
from canonical.launchpad.scripts.ftpmaster import (
    PackageLocationError, SoyuzScriptError)
from canonical.launchpad.scripts.create_rebuild import RebuildArchiveCreator
from canonical.testing import LaunchpadZopelessLayer


class TestStartRebuildScript(unittest.TestCase):
    """Test the copy-package.py script."""
    layer = LaunchpadZopelessLayer
    rebld_archive_name = "ra%s" % int(time.time())

    def runScript(self, extra_args=None):
        """Run start-rebuild.py, returning the result and output.

        Returns a tuple of the process's return code, stdout output and
        stderr output."""
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

    def isNameVacant(self, name):
        """Make sure the rebuild archive name to be used is vacant."""
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
        self.assertTrue(self.isNameVacant(self.rebld_archive_name) is None)

        [hoary] = getUtility(IDistroSeriesSet).findByName('hoary')

        pending_statuses = (
            PackagePublishingStatus.PENDING,
            PackagePublishingStatus.PUBLISHED)

        # These source packages will be copied to the rebuild archive.
        hoary_sources = hoary.distribution.main_archive.getPublishedSources(
            distroseries=hoary, status=pending_statuses)

        src_names = sorted(source.displayname for source in hoary_sources)
        expected_src_names = [u'alsa-utils 1.0.9a-4ubuntu1 in hoary',
            u'cnews cr.g7-37 in hoary', u'evolution 1.0 in hoary',
            u'libstdc++ b8p in hoary',
            u'linux-source-2.6.15 2.6.15.3 in hoary', 
            u'netapplet 1.0-1 in hoary', u'pmount 0.1-2 in hoary']
        self.assertEqual(src_names, expected_src_names)

        # Command line arguments required for the invocation of the
        # 'start-rebuild.py' script.
        extra_args = [
            '-d', 'ubuntu', '-s', 'hoary', '-c', 'main', '-t',
            '"rebuild archive from %s"' % datetime.ctime(datetime.utcnow()),
            '-r', self.rebld_archive_name, '-u', 'salgado']

        # Start rebuild now!
        (return_code, out, err) = self.runScript(extra_args)

        # Check for zero exit code.
        self.assertEqual(return_code, 0)

        # Make sure the rebuild archive with the desired name was
        # created
        rebuild_archive = self.isNameVacant(self.rebld_archive_name)
        self.assertTrue(rebuild_archive is not None)

        # Make sure the source packages were cloned.
        rebuild_sources = rebuild_archive.getPublishedSources(
            distroseries=hoary, status=pending_statuses)

        rebuild_src_names = sorted(
            source.displayname for source in rebuild_sources)

        self.assertEqual(rebuild_src_names, expected_src_names)

        def get_spn(binary_package):
            """Return the SourcePackageName of the binary."""
            pub = binary_package.getCurrentPublication()
            return pub.sourcepackagerelease.sourcepackagename

        # Now check that we have build records for the sources cloned.
        builds = list(getUtility(IBuildSet).getBuildsForArchive(
            rebuild_archive, status=BuildStatus.NEEDSBUILD))

        # Please note: there will be no build for the pmount package
        # since it is architecture independent and the 'hoary'
        # DistroSeries in the sample data has no DistroArchSeries
        # with chroots set up.
        expected_build_spns = [
            u'alsa-utils', u'cnews', u'evolution', u'libstdc++',
            u'linux-source-2.6.15', u'netapplet']
        build_spns = [
            get_spn(removeSecurityProxy(build)).name for build in builds]

        self.assertEqual(build_spns, expected_build_spns)

    def assertRaisesWithContent(self, exception, exception_content,
                                func, *args):
        """Check if the given exception is raised with given content.

        If the expection isn't raised or the exception_content doesn't
        match what was raised an AssertionError is raised.
        """
        exception_name = str(exception).split('.')[-1]
        print args

        try:
            func(*args)
        except exception, err:
            if not str(err).startswith(exception_content):
                raise AssertionError(
                    "'%s' was not the reason expected" % str(err))
        else:
            raise AssertionError(
                "'%s' was not raised" % exception_name)

    def testInvalidRebuildArchiveName(self):
        """Try rebuild with invalid archive name.

        The rebuild archive creation will fail with exit code 2.
        """
        now = int(time.time())
        # The colons in the name make it invalid.
        invalid_archive_name = "ra::%s" % now

        # Make sure a rebuild archive with the desired name does
        # not exist yet.
        self.assertTrue(self.isNameVacant(invalid_archive_name) is None)

        [hoary] = getUtility(IDistroSeriesSet).findByName('hoary')

        # Command line arguments required for the invocation of the
        # 'start-rebuild.py' script.
        extra_args = [
            '-d', 'ubuntu', '-s', 'hoary', '-c', 'main', '-t',
            '"rebuild archive from %s"' % datetime.ctime(datetime.utcnow()),
            '-r', invalid_archive_name, '-u', 'salgado']

        script = RebuildArchiveCreator(
            'start-rebuild', dbuser=config.uploader.dbuser,
            test_args=extra_args)
        self.assertRaisesWithContent(
            SoyuzScriptError, "Invalid rebuild archive name",
            script.mainTask)

        # Make sure the rebuild archive with the desired name was
        # not created
        rebuild_archive = self.isNameVacant(invalid_archive_name)
        self.assertTrue(rebuild_archive is None)

    def testInvalidComponentName(self):
        """Try rebuild with invalid component name.

        The rebuild archive creation will fail with exit code 3.
        """
        now = int(time.time())
        archive_name = "ra%s" % now

        # Make sure a rebuild archive with the desired name does
        # not exist yet.
        self.assertTrue(self.isNameVacant(archive_name) is None)

        [hoary] = getUtility(IDistroSeriesSet).findByName('hoary')

        invalid_component = "component/:/%s" % now
        # Command line arguments required for the invocation of the
        # 'start-rebuild.py' script.
        extra_args = [
            '-d', 'ubuntu', '-s', 'hoary', '-c', invalid_component, '-t',
            '"rebuild archive from %s"' % datetime.ctime(datetime.utcnow()),
            '-r', archive_name, '-u', 'salgado']

        script = RebuildArchiveCreator(
            'start-rebuild', dbuser=config.uploader.dbuser,
            test_args=extra_args)
        self.assertRaisesWithContent(
            SoyuzScriptError, "Invalid component name",
            script.mainTask)

        # Make sure the rebuild archive with the desired name was
        # not created
        rebuild_archive = self.isNameVacant(archive_name)
        self.assertTrue(rebuild_archive is None)

    def testInvalidSuite(self):
        """Try rebuild with invalid suite.

        The rebuild archive creation will fail with exit code 1.
        """
        now = int(time.time())
        archive_name = "ra%s" % now

        # Make sure a rebuild archive with the desired name does
        # not exist yet.
        self.assertTrue(self.isNameVacant(archive_name) is None)

        [hoary] = getUtility(IDistroSeriesSet).findByName('hoary')

        invalid_suite = "suite/:/%s" % now
        # Command line arguments required for the invocation of the
        # 'start-rebuild.py' script.
        extra_args = [
            '-d', 'ubuntu', '-s', invalid_suite, '-c', 'main', '-t',
            '"rebuild archive from %s"' % datetime.ctime(datetime.utcnow()),
            '-r', archive_name, '-u', 'salgado']

        script = RebuildArchiveCreator(
            'start-rebuild', dbuser=config.uploader.dbuser,
            test_args=extra_args)
        self.assertRaisesWithContent(
            PackageLocationError, "Could not find suite", 
            script.mainTask)

        # Make sure the rebuild archive with the desired name was
        # not created
        rebuild_archive = self.isNameVacant(archive_name)
        self.assertTrue(rebuild_archive is None)

    def testInvalidUserName(self):
        """Try rebuild with invalid user name.

        The rebuild archive creation will fail with exit code 4.
        """
        now = int(time.time())
        archive_name = "ra%s" % now

        # Make sure a rebuild archive with the desired name does
        # not exist yet.
        self.assertTrue(self.isNameVacant(archive_name) is None)

        [hoary] = getUtility(IDistroSeriesSet).findByName('hoary')

        invalid_user = "user/:/%s" % now
        # Command line arguments required for the invocation of the
        # 'start-rebuild.py' script.
        extra_args = [
            '-d', 'ubuntu', '-s', 'hoary', '-c', 'main', '-t',
            '"rebuild archive from %s"' % datetime.ctime(datetime.utcnow()),
            '-r', archive_name, '-u', invalid_user]

        script = RebuildArchiveCreator(
            'start-rebuild', dbuser=config.uploader.dbuser,
            test_args=extra_args)
        self.assertRaisesWithContent(
            SoyuzScriptError, "Invalid user name",
            script.mainTask)

        # Make sure the rebuild archive with the desired name was
        # not created
        rebuild_archive = self.isNameVacant(archive_name)
        self.assertTrue(rebuild_archive is None)

    def testXistingArchive(self):
        """Try rebuild with existing rebuild archive name.

        The rebuild archive creation will fail with exit code 5.
        """
        # Make sure a rebuild archive with the desired name does
        # not exist yet.
        self.assertFalse(self.isNameVacant(self.rebld_archive_name) is None)

        [hoary] = getUtility(IDistroSeriesSet).findByName('hoary')

        # Command line arguments required for the invocation of the
        # 'start-rebuild.py' script.
        extra_args = [
            '-d', 'ubuntu', '-s', 'hoary', '-c', 'main', '-t',
            '"rebuild archive from %s"' % datetime.ctime(datetime.utcnow()),
            '-r', self.rebld_archive_name, '-u', 'salgado']

        script = RebuildArchiveCreator(
            'start-rebuild', dbuser=config.uploader.dbuser,
            test_args=extra_args)
        self.assertRaisesWithContent(
            SoyuzScriptError, "An archive rebuild named",
            script.mainTask)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
