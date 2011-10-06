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

from canonical.config import config
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from canonical.testing.layers import (
    DatabaseLayer,
    LaunchpadZopelessLayer,
    )
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.model.buildfarmjob import BuildFarmJob
from lp.buildmaster.model.packagebuild import PackageBuild
from lp.registry.interfaces.distribution import IDistributionSet
from lp.services.log.logger import BufferLogger
from lp.services.scripts.base import LaunchpadScriptFailure
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
from lp.soyuz.scripts.buildd import (
    QueueBuilder,
    RetryDepwait,
    )
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher


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

    def runBuilddQueueBuilder(self, extra_args=None):
        if extra_args is None:
            extra_args = []
        return self.runCronscript("buildd-queue-builder.py", extra_args)

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


class TestQueueBuilder(TestCronscriptBase):
    """Test QueueBuilder buildd script class."""
    layer = LaunchpadZopelessLayer

    def getQueueBuilder(self, distribution=None, suites=None,
                        score_only=False):
        """Return a configured `QueueBuilder` script object."""
        test_args = ['-n']
        if distribution is not None:
            test_args.extend(['-d', distribution])

        if suites is not None:
            for suite in suites:
                test_args.extend(['-s', suite])

        if score_only:
            test_args.append('--score-only')

        queue_builder = QueueBuilder(
            name='queue-builder', test_args=test_args)
        queue_builder.logger = BufferLogger()

        return queue_builder

    def getSourceWithoutBuilds(self):
        """Create a source publication without builds in ubuntu/hoary.

        Once the source is created add the chroots needed for build
        creation.
        """
        test_publisher = SoyuzTestPublisher()

        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        hoary = ubuntu.getSeries('hoary')
        test_publisher.setUpDefaultDistroSeries(hoary)

        source = test_publisher.getPubSource()
        self.assertEqual(0, len(source.getBuilds()))

        test_publisher.addFakeChroots()
        return source

    def testCalculateDistroseries(self):
        # Distribution defaults to ubuntu and when suite is omitted
        # all series are considered in the ascending order.
        qb = self.getQueueBuilder()
        self.assertEqual(
            ['warty', 'hoary', 'grumpy', 'breezy-autotest'],
            [distroseries.name
             for distroseries in qb.calculateDistroseries()])

        # Distribution name can be defined.
        qb = self.getQueueBuilder(distribution='ubuntutest')
        self.assertEqual(
            ['breezy-autotest', 'hoary-test'],
            [distroseries.name
             for distroseries in qb.calculateDistroseries()])

        # Distribution/Suite arguments mismatch result in a error.
        qb = self.getQueueBuilder(distribution='boing')
        self.assertRaises(LaunchpadScriptFailure, qb.calculateDistroseries)

        qb = self.getQueueBuilder(suites=('hoary-test', ))
        self.assertRaises(LaunchpadScriptFailure, qb.calculateDistroseries)

        # A single valid suite argument results in a list with one
        # distroseries (pockets are completely ignored).
        qb = self.getQueueBuilder(suites=('warty-security', ))
        self.assertEqual(
            ['warty'],
            [distroseries.name
             for distroseries in qb.calculateDistroseries()])

        # Multiple suite arguments result in a ordered list of distroseries.
        qb = self.getQueueBuilder(suites=('hoary', 'warty-security'))
        self.assertEqual(
            ['warty', 'hoary'],
            [distroseries.name
             for distroseries in qb.calculateDistroseries()])

    def testOtherDistribution(self):
        # Restricting the build creation to another distribution
        # does not create any builds either.
        source = self.getSourceWithoutBuilds()
        queue_builder = self.getQueueBuilder(distribution='ubuntutest')
        queue_builder.main()
        self.assertEqual(0, len(source.getBuilds()))

    def testOtherDistroseries(self):
        # Restricting the build creation to another distroseries
        # does not create any builds.
        source = self.getSourceWithoutBuilds()
        queue_builder = self.getQueueBuilder(suites=('warty', ))
        queue_builder.main()
        self.assertEqual(0, len(source.getBuilds()))

    def testRightDistroseries(self):
        # A build is created when queue-builder is restricted to the
        # distroseries where the testing source is published
        source = self.getSourceWithoutBuilds()
        queue_builder = self.getQueueBuilder(suites=('hoary', ))
        queue_builder.main()
        self.assertEqual(1, len(source.getBuilds()))

    def testAllSeries(self):
        # A build is created when queue-builder is not restricted to any
        # specific distroseries.
        source = self.getSourceWithoutBuilds()
        queue_builder = self.getQueueBuilder()
        queue_builder.main()
        self.assertEqual(1, len(source.getBuilds()))

    def testScoringOnlyDoesNotCreateBuilds(self):
        # Passing '--score-only' doesn't create builds.
        source = self.getSourceWithoutBuilds()
        queue_builder = self.getQueueBuilder(score_only=True)
        queue_builder.main()
        self.assertEqual(0, len(source.getBuilds()))

    def testScoringOnlyWorks(self):
        # The source now has a build but lacks the corresponding
        # buildqueue record. It is created and scored in '--score-only'
        # mode.
        source = self.getSourceWithoutBuilds()
        [build] = source.createMissingBuilds()
        build.buildqueue_record.destroySelf()

        queue_builder = self.getQueueBuilder(score_only=True)
        queue_builder.main()
        self.assertEqual(2505, build.buildqueue_record.lastscore)

    def testRunQueueBuilder(self):
        # buildd-queue-builder script runs without errors.
        self.assertRuns(runner=self.runBuilddQueueBuilder)


class TestRetryDepwait(TestCronscriptBase):
    """Test RetryDepwait buildd script class."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Store the number of pending builds present before run the tests."""
        self.number_of_pending_builds = self.getPendingBuilds().count()

    def getPendingBuilds(self):
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        pending_builds = store.find(
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
