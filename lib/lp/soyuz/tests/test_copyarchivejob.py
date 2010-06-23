from canonical.testing import LaunchpadZopelessLayer

from lp.testing import TestCaseWithFactory

from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.model.copyarchivejob import CopyArchiveJob


class CopyArchiveJobTests(TestCaseWithFactory):
    """Tests for CopyArchiveJob."""

    layer = LaunchpadZopelessLayer

    def test_getOopsVars(self):
        archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        target_distroseries = self.factory.makeDistroSeries()
        source_pocket = PackagePublishingPocket.RELEASE
        target_pocket = PackagePublishingPocket.BACKPORTS
        source_user = self.factory.makePerson()
        job = CopyArchiveJob.create(
            archive, args['source_archive'].id,
            args['distroseries'].id, source_pocket.value,
            target_distroseries.id, target_pocket.value,
            args['target_component'].id, source_user_id=source_user.id)
        vars = job.getOopsVars()
        self.assertIn(('archive_id', archive.id), vars)
        self.assertIn(('archive_job_id', job.context.id), vars)
        self.assertIn(('archive_job_type', job.context.job_type.title), vars)
        self.assertIn(('source_archive_id', args['source_archive'].id), vars)
        self.assertIn(
            ('source_distroseries_id', args['distroseries'].id), vars)
        self.assertIn(
            ('target_distroseries_id', target_distroseries.id), vars)
        self.assertIn(('source_pocket_value', source_pocket.value), vars)
        self.assertIn(('target_pocket_value', target_pocket.value), vars)
        self.assertIn(
            ('target_component_id', args['target_component'].id), vars)
        self.assertIn(('source_user_id', source_user.id), vars)

    def makeDummyArgs(self):
        args = {}
        distro = self.factory.makeDistribution()
        args['distroseries'] = self.factory.makeDistroSeries(
            distribution=distro)
        args['pocket'] = self.factory.getAnyPocket()
        args['source_archive'] = self.factory.makeArchive(
            distribution=distro)
        args['target_component'] = self.factory.makeComponent()
        return args

    def test_create_only_creates_one(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        job = CopyArchiveJob.create(
            target_archive, args['source_archive'].id,
            args['distroseries'].id, args['pocket'].value,
            args['distroseries'].id, args['pocket'].value,
            args['target_component'].id)
        self.assertEqual(1, self._getJobCount())
        args = self.makeDummyArgs()
        new_job = CopyArchiveJob.create(
            target_archive, args['source_archive'].id,
            args['distroseries'].id, args['pocket'].value,
            args['distroseries'].id, args['pocket'].value,
            args['target_component'].id)
        self.assertEqual(job, new_job)
        self.assertEqual(1, self._getJobCount())

    def test_create_sets_source_archive_id(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        source_archive = self.factory.makeArchive()
        job = CopyArchiveJob.create(
            target_archive, source_archive.id,
            args['distroseries'].id, args['pocket'].value,
            args['distroseries'].id, args['pocket'].value,
            args['target_component'].id)
        self.assertEqual(
            source_archive.id, job.metadata['source_archive_id'])

    def test_create_sets_source_series_id(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        source_distroseries = self.factory.makeDistroSeries()
        job = CopyArchiveJob.create(
            target_archive, args['source_archive'].id,
            source_distroseries.id, args['pocket'].value,
            args['distroseries'].id, args['pocket'].value,
            args['target_component'].id)
        self.assertEqual(
            source_distroseries.id, job.metadata['source_distroseries_id'])

    def test_create_sets_source_pocket_value(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        source_pocket = PackagePublishingPocket.RELEASE
        target_pocket = PackagePublishingPocket.BACKPORTS
        job = CopyArchiveJob.create(
            target_archive, args['source_archive'].id,
            args['distroseries'].id, source_pocket.value,
            args['distroseries'].id, target_pocket.value,
            args['target_component'].id)
        self.assertEqual(
            source_pocket.value, job.metadata['source_pocket_value'])

    def test_create_sets_target_pocket_value(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        source_pocket = PackagePublishingPocket.RELEASE
        target_pocket = PackagePublishingPocket.BACKPORTS
        job = CopyArchiveJob.create(
            target_archive, args['source_archive'].id,
            args['distroseries'].id, source_pocket.value,
            args['distroseries'].id, target_pocket.value,
            args['target_component'].id)
        self.assertEqual(
            target_pocket.value, job.metadata['target_pocket_value'])

    def test_create_sets_target_distroseries_id(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        target_distroseries = self.factory.makeDistroSeries()
        job = CopyArchiveJob.create(
            target_archive, args['source_archive'].id,
            args['distroseries'].id, args['pocket'].value,
            target_distroseries.id, args['pocket'].value,
            args['target_component'].id)
        self.assertEqual(
            target_distroseries.id, job.metadata['target_distroseries_id'])

    def test_create_sets_target_component_id(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        target_component = self.factory.makeComponent()
        job = CopyArchiveJob.create(
            target_archive, args['source_archive'].id,
            args['distroseries'].id, args['pocket'].value,
            args['distroseries'].id, args['pocket'].value,
            target_component.id)
        self.assertEqual(
            target_component.id, job.metadata['target_component_id'])

    def test_doesnt_set_source_user_id_if_not_passed(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        job = CopyArchiveJob.create(
            target_archive, args['source_archive'].id,
            args['distroseries'].id, args['pocket'].value,
            args['distroseries'].id, args['pocket'].value,
            args['target_component'].id)
        self.assertNotIn('source_user_id', job.metadata)

    def test_sets_source_user_id(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        source_owner = self.factory.makePerson()
        job = CopyArchiveJob.create(
            target_archive, args['source_archive'].id,
            args['distroseries'].id, args['pocket'].value,
            args['distroseries'].id, args['pocket'].value,
            args['target_component'].id, source_user_id=source_owner.id)
        self.assertEqual(
            source_owner.id, job.metadata['source_user_id'])

    def _getJobs(self):
        """Return the pending CopyArchiveJobs as a list."""
        return list(CopyArchiveJob.iterReady())

    def _getJobCount(self):
        """Return the number of CopyArchiveJobs in the queue."""
        return len(self._getJobs())

    def test_run(self):
        """Test that CopyArchiveJob.run() actually copies the archive.

        We just make a simple test here, and rely on PackageCloner tests
        to cover the functionality.
        """
        distribution = self.factory.makeDistribution(name="foobuntu")
        distroseries = self.factory.makeDistroSeries(
            distribution=distribution, name="maudlin")
        source_archive_owner = self.factory.makePerson(name="source-owner")
        source_archive = self.factory.makeArchive(
            name="source", owner=source_archive_owner,
            purpose=ArchivePurpose.PPA, distribution=distribution)
        target_archive_owner = self.factory.makePerson()
        target_archive = self.factory.makeArchive(
            purpose=ArchivePurpose.COPY, owner=target_archive_owner,
            name="test-copy-archive", distribution=distribution,
            description="Test copy archive", enabled=False)

