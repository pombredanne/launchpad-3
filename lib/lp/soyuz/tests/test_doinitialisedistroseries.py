from canonical.testing import LaunchpadZopelessLayer
from zope.security.proxy import removeSecurityProxy

from lp.soyuz.model.doinitialisedistroseriesjob import (
    DoInitialiseDistroSeriesJob)
from lp.testing import TestCaseWithFactory
from lp.testing.fakemethod import FakeMethod


class DoInitialiseDistroSeriesJobTests(TestCaseWithFactory):
    """Test case for DoInitialiseDistroSeriesJob."""
    
    layer = LaunchpadZopelessLayer

    def test_getOopsVars(self):
        distroseries = self.factory.makeDistroSeries()
        job = DoInitialiseDistroSeriesJob.create(distroseries)
        vars = job.getOopsVars()
        self.assertIn(('distroseries_id', distroseries.id), vars)
        self.assertIn(('distroseries_job_id', job.context.id), vars)
        self.assertIn(('distroseries_job_type', job.context.job_type.title), vars)

    def _getJobs(self):
        """Return the pending DoFooJobs as a list."""
        return list(DoInitialiseDistroSeriesJob.iterReady())
        
    def _getJobCount(self):
        """Return the number of DoFooJobs in the queue."""
        return len(self._getJobs())
        
    def test_create_only_creates_one(self):
        distroseries = self.factory.makeDistroSeries()
        # If there's already a DoInitialiseDistroSeriesJob for a DistroSeries,
        # DoInitialiseDistroSeriesJob.create() won't create a new one.
        job = DoInitialiseDistroSeriesJob.create(distroseries)
    
        # There will now be one job in the queue.
        self.assertEqual(1, self._getJobCount())

        new_job = DoInitialiseDistroSeriesJob.create(distroseries)

        # The two jobs will in fact be the same job.
        self.assertEqual(job, new_job)
    
        # And the queue will still have a length of 1.
        self.assertEqual(1, self._getJobCount())

    def test_run(self):
        """Test that DoInitialiseDistroSeriesJob.run() actually
        initialises builds and copies from the parent."""
        distroseries = self.factory.makeDistroSeries()
	distroseries.fake_initialiseFromParent = FakeMethod(result=True)
        removeSecurityProxy(distroseries).initialiseFromParent = (
            distroseries.fake_initialiseFromParent)

        job = DoInitialiseDistroSeriesJob.create(distroseries)
        job.run()

        self.assertEqual(1, distroseries.fake_initialiseFromParent.call_count)

