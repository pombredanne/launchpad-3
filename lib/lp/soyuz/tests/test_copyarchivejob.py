from canonical.testing import LaunchpadZopelessLayer

from lp.testing import TestCaseWithFactory

from lp.soyuz.model.copyarchivejob import CopyArchiveJob


class CopyArchiveJobTests(TestCaseWithFactory):
    """Tests for CopyArchiveJob."""

    layer = LaunchpadZopelessLayer

    def test_getOopsVars(self):
        archive = self.factory.makeArchive()
        job = CopyArchiveJob.create(archive)
        vars = job.getOopsVars()
        self.assertIn(('archive_id', archive.id), vars)
        self.assertIn(('archive_job_id', job.context.id), vars)
        self.assertIn(('archive_job_type', job.context.job_type.title), vars)

    def test_create_only_creates_one(self):
        archive = self.factory.makeArchive()
        job = CopyArchiveJob.create(archive)
        self.assertEqual(1, self._getJobCount())
        new_job = CopyArchiveJob.create(archive)
        self.assertEqual(job, new_job)
        self.assertEqual(1, self._getJobCount())

    def _getJobs(self):
        """Return the pending CopyArchiveJobs as a list."""
        return list(CopyArchiveJob.iterReady())

    def _getJobCount(self):
        """Return the number of CopyArchiveJobs in the queue."""
        return len(self._getJobs())

    def test_run(self):
        """Test that CopyArchiveJob.run() actually copies the archive."""
        pass
