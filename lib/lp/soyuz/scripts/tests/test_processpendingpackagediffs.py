# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import os
import subprocess
import sys

from canonical.config import config
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.services.log.logger import BufferLogger
from lp.soyuz.scripts.packagediff import ProcessPendingPackageDiffs
from lp.soyuz.tests.soyuz import TestPackageDiffsBase


class TestProcessPendingPackageDiffsScript(TestPackageDiffsBase):
    """Test the process-pending-packagediffs.py script."""
    layer = LaunchpadZopelessLayer
    dbuser = config.uploader.dbuser

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

        :return the initialized script object using `BufferLogger` and
           the given parameters.
        """
        test_args = []
        if limit is not None:
            test_args.append('-l %s' % limit)

        diff_processor = ProcessPendingPackageDiffs(
            name='process-pending-packagediffs', test_args=test_args)
        diff_processor.logger = BufferLogger()
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
        pending_diffs = self.getPendingDiffs()
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
