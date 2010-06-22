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
