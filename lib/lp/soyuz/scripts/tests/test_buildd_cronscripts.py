# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""cronscripts/buildd-* tests."""

__metaclass__ = type

import logging
import os
import subprocess
import sys
from unittest import TestCase

from zope.component import getUtility

from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.model.buildfarmjob import BuildFarmJob
from lp.buildmaster.model.packagebuild import PackageBuild
from lp.services.config import config
from lp.services.database.lpstorm import IStore
from lp.services.log.logger import BufferLogger
from lp.services.scripts.base import LaunchpadScriptFailure
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
from lp.soyuz.scripts.buildd import RetryDepwait
from lp.testing.layers import (
    DatabaseLayer,
    LaunchpadZopelessLayer,
    )


class TestCronscriptBase(TestCase):
    """Buildd cronscripts test classes."""

    def runCronscript(self, name, extra_args):
        """Run given cronscript, returning the result and output.

        Always set verbosity level.
        """
        # Scripts will write to the database.  The test runner won't see
        # this and not know that the database needs restoring.
        DatabaseLayer.force_dirty_database()

        script = os.path.join(config.root, "cronscripts", name)
        args = [sys.executable, script, "-v"]
        args.extend(extra_args)
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return (process.returncode, stdout, stderr)

    def runBuilddRetryDepwait(self, extra_args=None):
        if extra_args is None:
            extra_args = []
        return self.runCronscript("buildd-retry-depwait.py", extra_args)

    def assertRuns(self, runner, *args):
        """Invokes given runner with given arguments.

        Asserts the result code is 0 (zero) and returns a triple containing:
        (result_code, standart_output, error_output).
        """
        rc, out, err = runner()
        self.assertEqual(0, rc, "Err:\n%s" % err)

        return rc, out, err


class TestRetryDepwait(TestCronscriptBase):
    """Test RetryDepwait buildd script class."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Store the number of pending builds present before run the tests."""
        self.number_of_pending_builds = self.getPendingBuilds().count()

    def getPendingBuilds(self):
        pending_builds = IStore(BinaryPackageBuild).find(
            BinaryPackageBuild,
            BinaryPackageBuild.package_build == PackageBuild.id,
            PackageBuild.build_farm_job == BuildFarmJob.id,
            BuildFarmJob.status == BuildStatus.NEEDSBUILD)
        return pending_builds

    def getRetryDepwait(self, distribution=None):
        test_args = ['-n']
        if distribution is not None:
            test_args.extend(['-d', distribution])

        retry_depwait = RetryDepwait(
            name='retry-depwait', test_args=test_args)
        retry_depwait.logger = BufferLogger()

        # `IBuildSet.retryDepwait` retrieve a specific logger instance
        # from the global registry, we have to silence that too.
        root_logger = logging.getLogger('retry-depwait')
        root_logger.setLevel(logging.CRITICAL)

        return retry_depwait

    def testUnknownDistribution(self):
        """A error is raised on unknown distributions."""
        retry_depwait = self.getRetryDepwait(distribution='foobar')
        self.assertRaises(LaunchpadScriptFailure, retry_depwait.main)

    def testRunRetryDepwait(self):
        """Check if actual buildd-retry-depwait script runs without errors."""
        self.assertRuns(runner=self.runBuilddRetryDepwait)

    def testEmptyRun(self):
        """Check the results of a run against pristine sampledata.

        Since the only record in MANUALDEPWAIT in sampledata can't be
        satisfied we expect the number of pending builds to be constant.
        """
        retry_depwait = self.getRetryDepwait()
        retry_depwait.main()
        self.assertEqual(
            self.number_of_pending_builds, self.getPendingBuilds().count())

    def testWorkingRun(self):
        """Modify sampledata and expects a new pending build to be created."""
        depwait_build = BinaryPackageBuild.get(12)

        # Moving the target source to universe, so it can reach the only
        # published binary we have in sampledata.
        source_release = depwait_build.distributionsourcepackagerelease
        pub = source_release.publishing_history[0]
        pub.component = getUtility(IComponentSet)['universe']

        # Make it dependend on the only binary that can be satisfied in
        # the sampledata.
        depwait_build.dependencies = u'pmount'

        self.layer.commit()

        retry_depwait = self.getRetryDepwait()
        retry_depwait.main()
        self.layer.commit()

        # Reload the build record after the multiple commits.
        depwait_build = BinaryPackageBuild.get(12)
        self.assertEqual(
            self.number_of_pending_builds + 1,
            self.getPendingBuilds().count())
        self.assertEqual(depwait_build.status.name, 'NEEDSBUILD')
        self.assertEqual(depwait_build.buildqueue_record.lastscore, 1755)
