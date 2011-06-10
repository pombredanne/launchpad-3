# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.adapters.packagelocation import PackageLocation
from lp.soyuz.enums import ArchivePurpose
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuildSet
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.model.copyarchivejob import CopyArchiveJob
from lp.soyuz.model.processor import ProcessorFamilySet
from lp.testing import (
    celebrity_logged_in,
    TestCaseWithFactory,
    )


class CopyArchiveJobTests(TestCaseWithFactory):
    """Tests for CopyArchiveJob."""

    layer = DatabaseFunctionalLayer

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
        self.assertIn(('merge', False), vars)

    def makeDummyArgs(self):
        args = {}
        distro = self.factory.makeDistribution()
        args['distroseries'] = self.factory.makeDistroSeries(
            distribution=distro)
        args['pocket'] = self.factory.getAnyPocket()
        args['source_archive'] = self.factory.makeArchive(
            distribution=distro)
        return args

    def test_error_if_already_exists(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        CopyArchiveJob.create(
            target_archive, args['source_archive'], args['distroseries'],
            args['pocket'], args['distroseries'], args['pocket'])
        self.assertEqual(1, self._getJobCount())
        args = self.makeDummyArgs()
        self.assertRaises(
            ValueError, CopyArchiveJob.create, target_archive,
            args['source_archive'], args['distroseries'], args['pocket'],
            args['distroseries'], args['pocket'])

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
            [f.name for f in [family1, family2]],
            job.metadata['proc_family_names'])

    def test_error_on_merge_with_proc_families(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        family1 = self.factory.makeProcessorFamily(name="armel")
        family2 = self.factory.makeProcessorFamily(name="ia64")
        self.assertRaises(
            ValueError, CopyArchiveJob.create, target_archive,
            args['source_archive'], args['distroseries'], args['pocket'],
            args['distroseries'], args['pocket'],
            proc_families=[family1, family2], merge=True)

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

    def test_create_sets_merge_False_by_default(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        job = CopyArchiveJob.create(
            target_archive, args['source_archive'], args['distroseries'],
            args['pocket'], args['distroseries'], args['pocket'])
        self.assertEqual(False, job.metadata['merge'])

    def test_create_sets_merge_True_on_request(self):
        target_archive = self.factory.makeArchive()
        args = self.makeDummyArgs()
        job = CopyArchiveJob.create(
            target_archive, args['source_archive'], args['distroseries'],
            args['pocket'], args['distroseries'], args['pocket'], merge=True)
        self.assertEqual(True, job.metadata['merge'])

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

    def makeSourceAndTarget(self):
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
        das = self.factory.makeDistroArchSeries(
            distroseries=distroseries, architecturetag="i386",
            processorfamily=ProcessorFamilySet().getByName("x86"),
            supports_virtualized=True)
        with celebrity_logged_in('admin'):
            distroseries.nominatedarchindep = das
        target_archive_owner = self.factory.makePerson()
        target_archive = self.factory.makeArchive(
            purpose=ArchivePurpose.COPY, owner=target_archive_owner,
            name="test-copy-archive", distribution=distribution,
            description="Test copy archive", enabled=False)
        return source_archive, target_archive, distroseries

    def checkPublishedSources(self, expected, archive, series):
        # We need to be admin as the archive is disabled at this point.
        with celebrity_logged_in('admin'):
            sources = archive.getPublishedSources(
                distroseries=series,
                status=(
                    PackagePublishingStatus.PENDING,
                    PackagePublishingStatus.PUBLISHED))
            actual = []
            for source in sources:
                actual.append(
                    (source.source_package_name,
                     source.source_package_version))
            self.assertEqual(sorted(expected), sorted(actual))

    def test_run(self):
        """Test that CopyArchiveJob.run() actually copies the archive.

        We just make a simple test here, and rely on PackageCloner tests
        to cover the functionality.
        """
        source_archive, target_archive, series = self.makeSourceAndTarget()
        job = CopyArchiveJob.create(
            target_archive, source_archive, series,
            PackagePublishingPocket.RELEASE, series,
            PackagePublishingPocket.RELEASE)
        job.run()
        self.checkPublishedSources([("bzr", "2.1")], target_archive, series)

    def test_run_mergeCopy(self):
        """Test that CopyArchiveJob.run() when merge=True does a mergeCopy."""
        source_archive, target_archive, series = self.makeSourceAndTarget()
        # Create the copy archive
        job = CopyArchiveJob.create(
            target_archive, source_archive, series,
            PackagePublishingPocket.RELEASE, series,
            PackagePublishingPocket.RELEASE)
        job.start()
        job.run()
        job.complete()
        # Now the two archives are in the same state, so we change the
        # source archive and request a merge to check that it works.
        # Create a new version of the apt package in the source
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=self.factory.getOrMakeSourcePackageName(
                name='apt'),
            distroseries=series, component=self.factory.makeComponent(),
            version="1.2", architecturehintlist='any',
            archive=source_archive, status=PackagePublishingStatus.PUBLISHED,
            pocket=PackagePublishingPocket.RELEASE)
        # Create a job to merge
        job = CopyArchiveJob.create(
            target_archive, source_archive, series,
            PackagePublishingPocket.RELEASE, series,
            PackagePublishingPocket.RELEASE, merge=True)
        job.run()
        # Check that the new apt package is in the target
        self.checkPublishedSources(
            [("bzr", "2.1"), ("apt", "1.2")], target_archive, series)

    def test_run_with_proc_families(self):
        """Test that a CopyArchiveJob job with proc_families uses them.

        If we create a CopyArchiveJob with proc_families != None then
        they should be used when cloning packages.
        """
        source_archive, target_archive, series = self.makeSourceAndTarget()
        proc_families = [ProcessorFamilySet().getByName("x86")]
        job = CopyArchiveJob.create(
            target_archive, source_archive, series,
            PackagePublishingPocket.RELEASE, series,
            PackagePublishingPocket.RELEASE, proc_families=proc_families)
        job.run()
        builds = list(
            getUtility(IBinaryPackageBuildSet).getBuildsForArchive(
            target_archive, status=BuildStatus.NEEDSBUILD))
        actual_builds = list()
        for build in builds:
            naked_build = removeSecurityProxy(build)
            spr = naked_build.source_package_release
            actual_builds.append(
                (spr.name, spr.version, naked_build.processor.family.name))
        # One build for the one package, as we specified one processor
        # family.
        self.assertEqual([("bzr", "2.1", "x86")], actual_builds)
