from zope.security.proxy import removeSecurityProxy

from canonical.testing import LaunchpadZopelessLayer

from lp.testing import TestCaseWithFactory

from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.adapters.packagelocation import PackageLocation
from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
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
        target_component = self.factory.makeComponent()
        job = CopyArchiveJob.create(
            archive, args['source_archive'], args['distroseries'],
            source_pocket, target_distroseries, target_pocket,
            target_component=target_component)
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
            ('target_component_id', target_component.id), vars)

    def makeDummyArgs(self):
        args = {}
        distro = self.factory.makeDistribution()
        args['distroseries'] = self.factory.makeDistroSeries(
            distribution=distro)
        args['pocket'] = self.factory.getAnyPocket()
        args['source_archive'] = self.factory.makeArchive(
            distribution=distro)
        return args

    def test_create_only_creates_one(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        job = CopyArchiveJob.create(
            target_archive, args['source_archive'], args['distroseries'],
            args['pocket'], args['distroseries'], args['pocket'])
        self.assertEqual(1, self._getJobCount())
        args = self.makeDummyArgs()
        new_job = CopyArchiveJob.create(
            target_archive, args['source_archive'], args['distroseries'],
            args['pocket'], args['distroseries'], args['pocket'])
        self.assertEqual(job, new_job)
        self.assertEqual(1, self._getJobCount())

    def test_create_sets_source_archive_id(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        source_archive = self.factory.makeArchive()
        job = CopyArchiveJob.create(
            target_archive, source_archive, args['distroseries'],
            args['pocket'], args['distroseries'], args['pocket'])
        self.assertEqual(
            source_archive.id, job.metadata['source_archive_id'])

    def test_create_sets_source_series_id(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        source_distroseries = self.factory.makeDistroSeries()
        job = CopyArchiveJob.create(
            target_archive, args['source_archive'], source_distroseries,
            args['pocket'], args['distroseries'], args['pocket'])
        self.assertEqual(
            source_distroseries.id, job.metadata['source_distroseries_id'])

    def test_create_sets_source_pocket_value(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        source_pocket = PackagePublishingPocket.RELEASE
        target_pocket = PackagePublishingPocket.BACKPORTS
        job = CopyArchiveJob.create(
            target_archive, args['source_archive'], args['distroseries'],
            source_pocket, args['distroseries'], target_pocket)
        self.assertEqual(
            source_pocket.value, job.metadata['source_pocket_value'])

    def test_create_sets_target_pocket_value(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        source_pocket = PackagePublishingPocket.RELEASE
        target_pocket = PackagePublishingPocket.BACKPORTS
        job = CopyArchiveJob.create(
            target_archive, args['source_archive'], args['distroseries'],
            source_pocket, args['distroseries'], target_pocket)
        self.assertEqual(
            target_pocket.value, job.metadata['target_pocket_value'])

    def test_create_sets_target_distroseries_id(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        target_distroseries = self.factory.makeDistroSeries()
        job = CopyArchiveJob.create(
            target_archive, args['source_archive'], args['distroseries'],
            args['pocket'], target_distroseries, args['pocket'])
        self.assertEqual(
            target_distroseries.id, job.metadata['target_distroseries_id'])

    def test_create_sets_target_component_id(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        target_component = self.factory.makeComponent()
        job = CopyArchiveJob.create(
            target_archive, args['source_archive'], args['distroseries'],
            args['pocket'], args['distroseries'], args['pocket'],
            target_component=target_component)
        self.assertEqual(
            target_component.id, job.metadata['target_component_id'])

    def test_create_sets_target_component_id_to_None_if_unspecified(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        job = CopyArchiveJob.create(
            target_archive, args['source_archive'], args['distroseries'],
            args['pocket'], args['distroseries'], args['pocket'])
        self.assertEqual(None, job.metadata['target_component_id'])

    def test_create_sets_proc_family_ids(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        family1 = self.factory.makeProcessorFamily(name="armel")
        family2 = self.factory.makeProcessorFamily(name="ia64")
        job = CopyArchiveJob.create(
            target_archive, args['source_archive'], args['distroseries'],
            args['pocket'], args['distroseries'], args['pocket'],
            proc_families=[family1, family2])
        self.assertEqual(
            [f.id for f in [family1, family2]],
            job.metadata['proc_family_ids'])

    def test_create_sets_source_package_set_ids(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        packagesets = [
            self.factory.makePackageset(),
            self.factory.makePackageset(),
        ]
        job = CopyArchiveJob.create(
            target_archive, args['source_archive'], args['distroseries'],
            args['pocket'], args['distroseries'], args['pocket'],
            packagesets=packagesets)
        self.assertEqual(
            [p.name for p in packagesets], job.metadata['packageset_names'])

    def test_get_source_location(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        source_distroseries = self.factory.makeDistroSeries()
        source_pocket = PackagePublishingPocket.RELEASE
        target_pocket = PackagePublishingPocket.BACKPORTS
        job = CopyArchiveJob.create(
            target_archive, args['source_archive'], source_distroseries,
            source_pocket, args['distroseries'], target_pocket)
        location = job.getSourceLocation()
        expected_location = PackageLocation(
            args['source_archive'], source_distroseries.distribution,
            source_distroseries, source_pocket)
        self.assertEqual(expected_location, location)

    def test_get_source_location_with_packagesets(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        source_distroseries = self.factory.makeDistroSeries()
        source_pocket = PackagePublishingPocket.RELEASE
        target_pocket = PackagePublishingPocket.BACKPORTS
        packagesets = [
            self.factory.makePackageset(),
            self.factory.makePackageset(),
        ]
        job = CopyArchiveJob.create(
            target_archive, args['source_archive'], source_distroseries,
            source_pocket, args['distroseries'], target_pocket,
            packagesets=packagesets)
        location = job.getSourceLocation()
        expected_location = PackageLocation(
            args['source_archive'], source_distroseries.distribution,
            source_distroseries, source_pocket, packagesets=packagesets)
        self.assertEqual(expected_location, location)

    def test_get_target_location(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        target_distroseries = self.factory.makeDistroSeries()
        source_pocket = PackagePublishingPocket.RELEASE
        target_pocket = PackagePublishingPocket.BACKPORTS
        job = CopyArchiveJob.create(
            target_archive, args['source_archive'], args['distroseries'],
            source_pocket, target_distroseries, target_pocket)
        location = job.getTargetLocation()
        expected_location = PackageLocation(
            target_archive, target_distroseries.distribution,
            target_distroseries, target_pocket)
        self.assertEqual(expected_location, location)

    def test_get_target_location_with_component(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        target_distroseries = self.factory.makeDistroSeries()
        source_pocket = PackagePublishingPocket.RELEASE
        target_pocket = PackagePublishingPocket.BACKPORTS
        target_component = self.factory.makeComponent()
        job = CopyArchiveJob.create(
            target_archive, args['source_archive'], args['distroseries'],
            source_pocket, target_distroseries, target_pocket,
            target_component=target_component)
        location = job.getTargetLocation()
        expected_location = PackageLocation(
            target_archive, target_distroseries.distribution,
            target_distroseries, target_pocket)
        expected_location.component = target_component
        self.assertEqual(expected_location, location)

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
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=self.factory.getOrMakeSourcePackageName(
                name='bzr'),
            distroseries=distroseries, component=self.factory.makeComponent(),
            version="2.1", architecturehintlist='any',
            archive=source_archive, status=PackagePublishingStatus.PUBLISHED,
            pocket=PackagePublishingPocket.RELEASE)
        target_archive_owner = self.factory.makePerson()
        target_archive = self.factory.makeArchive(
            purpose=ArchivePurpose.COPY, owner=target_archive_owner,
            name="test-copy-archive", distribution=distribution,
            description="Test copy archive", enabled=False)
        target_component = self.factory.makeComponent()
        job = CopyArchiveJob.create(
            target_archive, source_archive, distroseries,
            PackagePublishingPocket.RELEASE, distroseries,
            PackagePublishingPocket.RELEASE)
        job.run()
        sources = target_archive.getPublishedSources(
            distroseries=distroseries,
            status=(
                PackagePublishingStatus.PENDING,
                PackagePublishingStatus.PUBLISHED))
        actual = []
        for source in sources:
            source = removeSecurityProxy(source)
            actual.append(
                (source.source_package_name, source.source_package_version))
        self.assertEqual([("bzr", "2.1")], actual)
