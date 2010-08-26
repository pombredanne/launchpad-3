# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from canonical.testing import LaunchpadZopelessLayer
from zope.security.proxy import removeSecurityProxy

from lp.soyuz.model.dodistributionjob import (
    DoDistributionJob)
from lp.soyuz.scripts.initialise_distroseries import InitialisationError
from lp.testing import TestCaseWithFactory


class DoDistributionJobTests(TestCaseWithFactory):
    """Test case for DoDistributionJob."""
    
    layer = LaunchpadZopelessLayer

    def test_getOopsVars(self):
        distribution = self.factory.makeDistribution()
        distroseries = self.factory.makeDistroSeries(
            distribution=distribution)
        job = DoDistributionJob.create(distribution, distroseries)
        vars = job.getOopsVars()
        self.assertIn(('distribution_id', distribution.id), vars)
        self.assertIn(('distroseries_id', distroseries.id), vars)
        self.assertIn(('distribution_job_id', job.context.id), vars)

    def _getJobs(self):
        """Return the pending DoDistributionJobs as a list."""
        return list(DoDistributionJob.iterReady())
        
    def _getJobCount(self):
        """Return the number of DoDistributionJobs in the queue."""
        return len(self._getJobs())
        
    def test_create_only_creates_one(self):
        distribution = self.factory.makeDistribution()
        distroseries = self.factory.makeDistroSeries(
            distribution=distribution)
        # If there's already a DoDistributionJob for a Distribution,
        # DoDistributionJob.create() won't create a new one.
        job = DoDistributionJob.create(distribution, distroseries)
    
        # There will now be one job in the queue.
        self.assertEqual(1, self._getJobCount())

        new_job = DoDistributionJob.create(distribution, distroseries)

        # The two jobs will in fact be the same job.
        self.assertEqual(job, new_job)
    
        # And the queue will still have a length of 1.
        self.assertEqual(1, self._getJobCount())

    def test_run(self):
        """Test that DoDistributionJob.run() actually
        initialises builds and copies from the parent."""
        distribution = self.factory.makeDistribution()
        distroseries = self.factory.makeDistroSeries(
            distribution=distribution)

        job = DoDistributionJob.create(distribution, distroseries)

        # Since our new distroseries doesn't have a parent set, and the first
        # thing that run() will execute is checking the distroseries, if it
        # returns an InitialisationError, then it's good.
        self.assertRaisesWithContent(
            InitialisationError, "Parent series required.", job.run)
