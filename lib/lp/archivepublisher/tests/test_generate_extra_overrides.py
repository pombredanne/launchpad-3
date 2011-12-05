# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for the `generate-contents-files` script."""

__metaclass__ = type

from optparse import OptionValueError
import os
import tempfile

from canonical.testing.layers import (
    LaunchpadZopelessLayer,
    ZopelessDatabaseLayer,
    )
from lp.archivepublisher.scripts.generate_extra_overrides import (
    AtomicFile,
    GenerateExtraOverrides,
    )
from lp.archivepublisher.utils import RepositoryIndexFile
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
from lp.services.log.logger import DevNullLogger
from lp.services.osutils import open_for_writing
from lp.services.scripts.base import LaunchpadScriptFailure
from lp.services.utils import file_exists
from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.faketransaction import FakeTransaction


def file_contents(path):
    """Return the contents of the file at path."""
    with open(path) as handle:
        return handle.read()


class TestAtomicFile(TestCaseWithFactory):
    """Tests for the AtomicFile helper class."""

    layer = ZopelessDatabaseLayer

    def test_atomic_file_creates_file(self):
        # AtomicFile creates the named file with the requested contents.
        self.useTempDir()
        filename = self.factory.getUniqueString()
        text = self.factory.getUniqueString()
        with AtomicFile(filename) as test:
            test.write(text)
        self.assertEqual(text, file_contents(filename))

    def test_atomic_file_removes_dot_new(self):
        # AtomicFile does not leave .new files lying around.
        self.useTempDir()
        filename = self.factory.getUniqueString()
        with AtomicFile(filename):
            pass
        self.assertFalse(file_exists("%s.new" % filename))


class TestGenerateExtraOverrides(TestCaseWithFactory):
    """Tests for the actual `GenerateExtraOverrides` script."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestGenerateExtraOverrides, self).setUp()
        self._seeddir = self.makeTemporaryDirectory()

    def assertFilesEqual(self, expected_path, observed_path):
        self.assertEqual(
            file_contents(expected_path), file_contents(observed_path))

    def makeDistro(self, purpose=ArchivePurpose.PRIMARY):
        """Create a distribution for testing.

        The distribution will have a root directory set up, which will
        be cleaned up after the test.  It will have an attached archive.
        """
        distro = self.factory.makeDistribution(
            publish_root_dir=unicode(self.makeTemporaryDirectory()))
        self.factory.makeArchive(distribution=distro, purpose=purpose)
        return distro

    def makeScript(self, distribution=None, run_setup=True):
        """Create a script for testing."""
        if distribution is None:
            distribution = self.makeDistro()
        script = GenerateExtraOverrides(test_args=['-d', distribution.name])
        script.logger = DevNullLogger()
        script.txn = FakeTransaction()
        if run_setup:
            script.setUp()
        else:
            script.distribution = distribution
        return script

    def makePackage(self, dases, **kwargs):
        """Create a published source and binary package for testing."""
        package = self.factory.makeDistributionSourcePackage(
            distroseries=dases[0].distroseries)
        spph = self.factory.makeSourcePackagePublishingHistory(
            distroseries=dases[0].distroseries,
            pocket=PackagePublishingPocket.RELEASE,
            status=PackagePublishingStatus.PUBLISHED,
            sourcepackagename=package.name)
        for das in dases:
            build = self.factory.makeBinaryPackageBuild(
                source_package_release=spph.sourcepackagerelease,
                processor=das.default_processor)
            bpr = self.factory.makeBinaryPackageRelease(
                binarypackagename=package.name, build=build, **kwargs)
            self.factory.makeBinaryPackagePublishingHistory(
                binarypackagerelease=bpr, distroarchseries=das,
                status=PackagePublishingStatus.RELEASE)
        return package

    def makeIndexFiles(self, script, distroseries):
        """Create a limited subset of index files for testing."""
        for component in distroseries.components:
            index_root = os.path.join(
                script.config.distsroot, distroseries.name, component.name)

            source_index_root = os.path.join(index_root, 'source')
            source_index = RepositoryIndexFile(
                source_index_root, self._config.temproot, 'Packages')
            for spp in distroseries.getSourcePackagePublishing(
                PackagePublishingStatus.PUBLISHED, component=component):
                stanza = spp.getIndexStanza().encode('utf-8') + '\n\n'
                source_index.write(stanza)
            source_index.close()

            for arch in distroseries.architectures:
                package_index_root = os.path.join(
                    index_root, 'binary-%s' % arch.architecturetag)
                package_index = RepositoryIndexFile(
                    package_index_root, self._config.temproot, 'Packages')
                for bpp in distroseries.getBinaryPackagePublishing(
                    archtag=arch.architecturetag, component=component):
                    stanza = bpp.getIndexStanza().encode('utf-8') + '\n\n'
                    package_index.write(stanza)
                package_index.close()

    def makeSeedStructure(self, flavour, seed_names, seed_inherit=None):
        """Create a simple seed structure file."""
        if seed_inherit is None:
            seed_inherit = {}

        structure_path = os.path.join(self._seeddir, flavour, 'STRUCTURE')
        with open_for_writing(structure_path, 'w') as structure:
            for seed_name in seed_names:
                print >>structure, '%s: %s' % (
                    seed_name, seed_inherit[seed_name])

    def makeSeed(self, flavour, seed_name, entries, headers=None):
        """Create a simple seed file."""
        seed_path = os.path.join(self._seeddir, flavour, seed_name)
        with open_for_writing(seed_path, 'w') as seed:
            if headers is None:
                for header in headers:
                    print >>seed, header
                print >>seed
            for entry in entries:
                print ' * %s' % entry

    def test_name_is_consistent(self):
        # Script instances for the same distro get the same name.
        distro = self.factory.makeDistribution()
        self.assertEqual(
            GenerateExtraOverrides(test_args=['-d', distro.name]).name,
            GenerateExtraOverrides(test_args=['-d', distro.name]).name)

    def test_name_is_unique_for_each_distro(self):
        # Script instances for different distros get different names.
        self.assertNotEqual(
            GenerateExtraOverrides(
                test_args=['-d', self.factory.makeDistribution().name]).name,
            GenerateExtraOverrides(
                test_args=['-d', self.factory.makeDistribution().name]).name)

    def test_requires_distro(self):
        # The --distribution or -d argument is mandatory.
        script = GenerateExtraOverrides(test_args=[])
        self.assertRaises(OptionValueError, script.processOptions)

    def test_requires_real_distro(self):
        # An incorrect distribution name is flagged as an invalid option
        # value.
        script = GenerateExtraOverrides(
            test_args=['-d', self.factory.getUniqueString()])
        self.assertRaises(OptionValueError, script.processOptions)

    def test_looks_up_distro(self):
        # The script looks up and keeps the distribution named on the
        # command line.
        distro = self.makeDistro()
        script = self.makeScript(distro)
        self.assertEqual(distro, script.distribution)

    def test_prefers_development_distro_series(self):
        # The script prefers a DEVELOPMENT series for the named
        # distribution over CURRENT and SUPPORTED series.
        distro = self.makeDistro()
        self.factory.makeDistroSeries(distro, status=SeriesStatus.SUPPORTED)
        self.factory.makeDistroSeries(distro, status=SeriesStatus.CURRENT)
        development_distroseries = self.factory.makeDistroSeries(
            distro, status=SeriesStatus.DEVELOPMENT)
        script = self.makeScript(distro)
        self.assertEqual(development_distroseries, script.series)

    def test_permits_frozen_distro_series(self):
        # If there is no DEVELOPMENT series, a FROZEN one will do.
        distro = self.makeDistro()
        self.factory.makeDistroSeries(distro, status=SeriesStatus.SUPPORTED)
        self.factory.makeDistroSeries(distro, status=SeriesStatus.CURRENT)
        frozen_distroseries = self.factory.makeDistroSeries(
            distro, status=SeriesStatus.FROZEN)
        script = self.makeScript(distro)
        self.assertEqual(frozen_distroseries, script.series)

    def test_requires_development_frozen_distro_series(self):
        # If there is no DEVELOPMENT or FROZEN series, the script fails.
        distro = self.makeDistro()
        self.factory.makeDistroSeries(distro, status=SeriesStatus.SUPPORTED)
        self.factory.makeDistroSeries(distro, status=SeriesStatus.CURRENT)
        script = self.makeScript(distro, run_setup=False)
        self.assertRaises(LaunchpadScriptFailure, script.processOptions)

    def test_components_exclude_partner(self):
        # If a 'partner' component exists, it is excluded.
        distro = self.makeDistro()
        distroseries = self.factory.makeDistroSeries(distro)
        self.factory.makeComponentSelection(
            distroseries=distroseries, component="main")
        self.factory.makeComponentSelection(
            distroseries=distroseries, component="partner")
        script = self.makeScript(distro)
        self.assertEqual(["main"], script.components)

    def test_require_primary_archive(self):
        # The script fails if no PRIMARY archive exists.
        distro = self.makeDistro(purpose=ArchivePurpose.PARTNER)
        script = self.makeScript(distro, run_setup=False)
        script.processOptions()
        self.assertRaises(LaunchpadScriptFailure, script.getConfig)

    def test_output_path_in_germinateroot(self):
        # Output files are written to the correct locations under
        # germinateroot.
        distro = self.makeDistro()
        distroseries = self.factory.makeDistroSeries(distro)
        script = self.makeScript(distro)
        flavour = self.factory.getUniqueString()
        arch = self.factory.getUniqueString()
        base = self.factory.getUniqueString()
        output = script.outputPath(flavour, distroseries.name, arch, base)
        self.assertEqual(
            '%s/%s_%s_%s_%s' % (
                script.config.germinateroot, base, flavour, distroseries.name,
                arch),
            output)

    def runGerminate(self, script, series_name, arch, flavours):
        """Helper function to call script.runGerminate and return overrides."""
        structures = script.makeSeedStructures(
            series_name, flavours, seed_bases=[self._seeddir])

        override_fd, override_path = tempfile.mkstemp()
        try:
            script.runGerminate(
                override_fd, series_name, [arch], flavours, structures)
        finally:
            override_fd.close()
        return file_contents(override_path)

    def test_germinate_output(self):
        # A single call to runGerminate produces output for all flavours on
        # one architecture.
        distro = self.makeDistro()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        series_name = distroseries.name
        das = self.factory.makeDistroArchSeries(distroseries=distroseries)
        arch = das.architecturetag
        one = self.makePackage([das])
        two = self.makePackage([das])

        flavour_one = self.factory.getUniqueString()
        flavour_two = self.factory.getUniqueString()
        seed = self.factory.getUniqueString()
        self.makeSeedStructure(flavour_one, [seed])
        self.makeSeed(flavour_one, seed, [one.name])
        self.makeSeedStructure(flavour_two, [seed])
        self.makeSeed(flavour_two, seed, [two.name])

        script = self.makeScript(distro)
        overrides = self.runGerminate(
            script, series_name, arch, [flavour_one, flavour_two])
        self.assertTrue('', overrides)

        seed_dir_one = os.path.join(self._seeddir, flavour_one)
        self.assertFilesEqual(
            os.path.join(seed_dir_one, 'STRUCTURE'),
            script.outputPath(flavour_one, series_name, arch, 'structure'))
        self.assertTrue(file_exists(script.outputPath(
            flavour_one, series_name, arch, 'all')))
        self.assertTrue(file_exists(script.outputPath(
            flavour_one, series_name, arch, 'all.sources')))
        self.assertTrue(file_exists(script.outputPath(
            flavour_one, series_name, arch, seed)))

        seed_dir_two = os.path.join(self._seeddir, flavour_two)
        self.assertFilesEqual(
            os.path.join(seed_dir_two, 'STRUCTURE'),
            script.outputPath(flavour_two, series_name, arch, 'structure'))
        self.assertTrue(file_exists(script.outputPath(
            flavour_two, series_name, arch, 'all')))
        self.assertTrue(file_exists(script.outputPath(
            flavour_two, series_name, arch, 'all.sources')))
        self.assertTrue(file_exists(script.outputPath(
            flavour_two, series_name, arch, seed)))

    def test_germinate_output_task(self):
        # runGerminate produces Task extra overrides.
        distro = self.makeDistro()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        series_name = distroseries.name
        das = self.factory.makeDistroArchSeries(distroseries=distroseries)
        arch = das.architecturetag
        one = self.makePackage([das])
        two = self.makePackage([das], depends=one.name)
        three = self.makePackage([das])
        self.makePackage([das])
        script = self.makeScript(distro)
        self.makeIndexFiles(script, distroseries)

        flavour = self.factory.getUniqueString()
        seed_one = self.factory.getUniqueString()
        seed_two = self.factory.getUniqueString()
        self.makeSeedStructure(flavour, [seed_one, seed_two])
        self.makeSeed(
            flavour, seed_one, [two.name], headers=['Task-Description: one'])
        self.makeSeed(
            flavour, seed_two, [three.name], headers=['Task-Description: two'])

        overrides = self.runGerminate(script, series_name, [arch], [flavour])
        expected_overrides = [
            (one.name, '%s/%s  Task  %s' % (one.name, arch, seed_one)),
            (two.name, '%s/%s  Task  %s' % (two.name, arch, seed_one)),
            (three.name, '%s/%s  Task  %s' % (three.name, arch, seed_two)),
            ]
        expected_overrides = map(
            lambda x: x[1], sorted(expected_overrides, key=lambda x: x[0]))
        self.assertEqual(expected_overrides, overrides)

    def test_germinate_output_task_name(self):
        # The Task-Name field is honoured.
        distro = self.makeDistro()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        series_name = distroseries.name
        das = self.factory.makeDistroArchSeries(distroseries=distroseries)
        arch = das.architecturetag
        package = self.makePackage([das])
        script = self.makeScript(distro)
        self.makeIndexFiles(script, distroseries)

        flavour = self.factory.getUniqueString()
        seed_one = self.factory.getUniqueString()
        task_one = self.factory.getUniqueString()
        self.makeSeedStructure(flavour, [seed_one])
        self.makeSeed(
            flavour, seed_one, [package.name],
            headers=['Task-Name: %s' % task_one])

        overrides = self.runGerminate(script, series_name, [arch], [flavour])
        self.assertEqual(
            ['%s/%s  Task  %s' % (package.name, arch, task_one)], overrides)

    def test_germinate_output_task_per_derivative(self):
        # The Task-Per-Derivative field is honoured.
        distro = self.makeDistro()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        series_name = distroseries.name
        das = self.factory.makeDistroArchSeries(distroseries=distroseries)
        arch = das.architecturetag
        package = self.makePackage([das])
        script = self.makeScript(distro)
        self.makeIndexFiles(script, distroseries)

        flavour_one = self.factory.getUniqueString()
        flavour_two = self.factory.getUniqueString()
        seed_one = self.factory.getUniqueString()
        seed_two = self.factory.getUniqueString()
        self.makeSeedStructure(flavour_one, [seed_one, seed_two])
        self.makeSeed(flavour_one, seed_one, [package.name])
        self.makeSeed(
            flavour_one, seed_two, [package.name],
            headers=['Task-Per-Derivative: 1'])
        self.makeSeedStructure(flavour_two, [seed_one, seed_two])
        self.makeSeed(flavour_two, seed_one, [package.name])
        self.makeSeed(
            flavour_two, seed_two, [package.name],
            headers=['Task-Per-Derivative: 1'])

        overrides = self.runGerminate(
            script, series_name, [arch], [flavour_one, flavour_two])
        # seed_one is not per-derivative, so it is honoured only for
        # flavour_one and has a global name.  seed_two is per-derivative, so
        # it is honoured for both flavours and has the flavour name
        # prefixed.
        expected_overrides = [
            '%s/%s  Task  %s' % (package.name, arch, seed_one),
            '%s/%s  Task  %s-%s' % (package.name, arch, flavour_one, seed_two),
            '%s/%s  Task  %s-%s' % (package.name, arch, flavour_two, seed_two),
            ]
        self.assertEqual(expected_overrides, overrides)

    def test_germinate_output_task_seeds(self):
        # The Task-Seeds field is honoured.
        distro = self.makeDistro()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        series_name = distroseries.name
        das = self.factory.makeDistroArchSeries(distroseries=distroseries)
        arch = das.architecturetag
        one = self.makePackage([das])
        two = self.makePackage([das])
        script = self.makeScript(distro)
        self.makeIndexFiles(script, distroseries)

        flavour = self.factory.getUniqueString()
        seed_one = self.factory.getUniqueString()
        seed_two = self.factory.getUniqueString()
        self.makeSeedStructure(
            flavour, [seed_one, seed_two], seed_inherit={seed_two: seed_one})
        self.makeSeed(flavour, seed_one, [one.name])
        self.makeSeed(
            flavour, seed_two, [two.name],
            headers=['Task-Seeds: %s' % seed_one])

        overrides = self.runGerminate(script, series_name, [arch], [flavour])
        expected_overrides = [
            (one.name, '%s/%s  Task  %s' % (one.name, arch, seed_two)),
            (two.name, '%s/%s  Task  %s' % (two.name, arch, seed_two)),
            ]
        expected_overrides = map(
            lambda x: x[1], sorted(expected_overrides, key=lambda x: x[0]))
        self.assertEqual(expected_overrides, overrides)

    def test_germinate_output_build_essential(self):
        # runGerminate produces Build-Essential extra overrides.
        distro = self.makeDistro()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        series_name = distroseries.name
        das = self.factory.makeDistroArchSeries(distroseries=distroseries)
        arch = das.architecturetag
        package = self.makePackage([das])
        script = self.makeScript(distro)
        self.makeIndexFiles(script, distroseries)

        flavour = self.factory.getUniqueString()
        seed = "build-essential"
        self.makeSeedStructure(flavour, [seed])
        self.makeSeed(flavour, seed, [package.name])

        overrides = self.runGerminate(script, series_name, [arch], [flavour])
        self.assertEqual(
            ['%s/%s  Build-Essential  yes' % (package.name, arch)], overrides)

    def test_main(self):
        # If run end-to-end, the script generates override files containing
        # output for all architectures.
        distro = self.makeDistro()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        series_name = distroseries.name
        das_one = self.factory.makeDistroArchSeries(distroseries=distroseries)
        arch_one = das_one.architecturetag
        das_two = self.factory.makeDistroArchSeries(distroseries=distroseries)
        arch_two = das_two.architecturetag
        package = self.makePackage([das_one, das_two])
        script = self.makeScript(distro)
        self.makeIndexFiles(script, distroseries)

        flavour = self.factory.getUniqueString()
        seed = self.factory.getUniqueString()
        self.makeSeedStructure(flavour, [seed])
        self.makeSeed(
            flavour, seed, [package.name], headers=['Task-Description: task'])

        self.process(seed_bases=[self._seeddir])
        override_path = os.path.join(
            script.config.miscroot,
            "more-extra.override.%s.main" % series_name)
        expected_overrides = []
        for arch in sorted([arch_one, arch_two]):
            expected_overrides.append(
                '%s/%s  Task  %s' % (package.name, arch, seed))
        self.assertEqual(expected_overrides, file_contents(override_path))

    def test_run_script(self):
        # The script will run stand-alone.
        from canonical.launchpad.scripts.tests import run_script
        retval, out, err = run_script(
            'cronscripts/generate-extra-overrides.py', ['-d', 'ubuntu', '-q'])
        self.assertEqual(0, retval)
