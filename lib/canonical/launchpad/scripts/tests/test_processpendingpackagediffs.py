# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import os
import subprocess
import sys
import unittest

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.ftests import import_public_test_keys
from canonical.launchpad.interfaces import (
    IDistributionSet, IPackageDiffSet)
from canonical.launchpad.testing.fakepackager import FakePackager
from canonical.launchpad.scripts import QuietFakeLogger
from canonical.launchpad.scripts.packagediff import (
    ProcessPendingPackageDiffs)
from canonical.launchpad.database import LibraryFileAlias
from canonical.testing import LaunchpadZopelessLayer


class TestProcessPendingPackageDiffsScript(unittest.TestCase):
    """Test the process-pending-packagediffs.py script."""
    layer = LaunchpadZopelessLayer
    dbuser = config.uploader.dbuser

    def setUp(self):
        """Setup proper DB connection and contents for tests

        Connect to the DB as the 'uploader' user (same user used in the
        script), upload the test packages (see `uploadTestPackages`) and
        commit the transaction.

        Store the `FakePackager` object used in the test uploads as `packager`
        so the tests can reuse it if necessary.
        """
        self.layer.alterConnection(dbuser='launchpad')

        fake_chroot = LibraryFileAlias.get(1)
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        warty = ubuntu.getSeries('warty')
        warty['i386'].addOrUpdateChroot(fake_chroot)

        self.layer.txn.commit()

        self.layer.alterConnection(dbuser=self.dbuser)
        self.packager = self.uploadTestPackages()
        self.layer.txn.commit()

    def uploadTestPackages(self):
        """Upload packages for testing `PackageDiff` generation script.

        Upload zeca_1.0-1 and zeca_1.0-2 sources, so a `PackageDiff` between
        them is created.

        Assert there is not pending `PackageDiff` in the DB before uploading
        the package and also assert that there is one after the uploads.

        :return: the FakePackager object used to generate and upload the test,
            packages, so the tests can upload subsequent version if necessary.
        """
        # No pending PackageDiff available in sampledata.
        self.assertEqual(self.getPendingDiffs().count(), 0)

        import_public_test_keys()
        # Use FakePackager to upload a base package to ubuntu.
        packager = FakePackager(
            'zeca', '1.0', 'foo.bar@canonical.com-passwordless.sec')
        packager.buildUpstream()
        packager.buildSource()
        packager.uploadSourceVersion('1.0-1', suite="warty-updates")

        # Upload a new version of the source, so a PackageDiff can
        # be created.
        packager.buildVersion('1.0-2', changelog_text="cookies")
        packager.buildSource(include_orig=False)
        packager.uploadSourceVersion('1.0-2', suite="warty-updates")

        # Check if there is exactly one pending PackageDiff record and
        # It's the one we have just created.
        self.assertEqual(self.getPendingDiffs().count(), 1)

        return packager

    def getPendingDiffs(self):
        """Pending `PackageDiff` available."""
        return getUtility(IPackageDiffSet).getPendingDiffs()

    def runProcessPendingPackageDiffs(self, extra_args=None):
        """Run process-pending-packagediffs.py.

        Returns a tuple of the process's return code, stdout output and
        stderr output."""
        if extra_args is None:
            extra_args = []
        script = os.path.join(
            config.root, "cronscripts", "process-pending-packagediffs.py")
        args = [sys.executable, script]
        args.extend(extra_args)
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return (process.returncode, stdout, stderr)

    def testSimpleScriptRun(self):
        """Try a simple processing-pending-packagediffs.py run."""
        returncode, out, err = self.runProcessPendingPackageDiffs()
        if returncode != 0:
            print "\nStdout:\n%s\nStderr\n%s\n" % (out, err)
        self.assertEqual(0, returncode)

        self.layer.txn.abort()

        # The pending PackageDiff request was processed.
        self.assertEqual(self.getPendingDiffs().count(), 0)

    def getDiffProcessor(self, limit=None):
        """Return a `ProcessPendingPackageDiffs` instance.

        :param limit: if passed, it will be used as the 'limit' script
           argument.

        :return the initialised script object using `QuietFakeLogger` and
           the given parameters.
        """
        test_args = []
        if limit is not None:
            test_args.append('-l %s' % limit)

        diff_processor = ProcessPendingPackageDiffs(
            name='process-pending-packagediffs', test_args=test_args)
        diff_processor.logger = QuietFakeLogger()
        diff_processor.txn = self.layer.txn
        return diff_processor

    def testSimpleRun(self):
        """Simple run of the script class.

        The only diff available is processed after its run.
        """
        # Setup a DiffProcessor.
        diff_processor = self.getDiffProcessor()
        diff_processor.main()

        # The pending PackageDiff request was processed.
        # See doc/package-diff.txt for more information.
        pending_diffs = getUtility(IPackageDiffSet).getPendingDiffs()
        self.assertEqual(pending_diffs.count(), 0)

    def testLimitedRun(self):
        """Run the script with a limited scope.

        Check if a limited run of the script only processes up to 'limit'
        pending diff records and exits.
        """
        # Setup a DiffProcessor limited to one request per run.
        diff_processor = self.getDiffProcessor(limit=1)

        # Upload a new source version, so we have two pending PackageDiff
        # records to process.
        self.packager.buildVersion('1.0-3', changelog_text="biscuits")
        self.packager.buildSource(include_orig=False)
        self.packager.uploadSourceVersion('1.0-3', suite="warty-updates")
        self.assertEqual(self.getPendingDiffs().count(), 2)

        # The first processor run will process only one PackageDiff,
        # the other will remain.
        diff_processor.main()
        self.assertEqual(self.getPendingDiffs().count(), 1)

        # The next run process the remaining one.
        diff_processor.main()
        self.assertEqual(self.getPendingDiffs().count(), 0)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
