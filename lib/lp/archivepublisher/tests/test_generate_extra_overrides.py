# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for the `generate-extra-overrides` script."""

__metaclass__ = type

import logging
from optparse import OptionValueError
import os
import tempfile

from germinate import (
    archive,
    germinator,
    seeds,
    )
import transaction

from canonical.testing.layers import (
    LaunchpadZopelessLayer,
    ZopelessDatabaseLayer,
    )
from lp.archivepublisher.scripts.generate_extra_overrides import (
    AtomicFile,
    CachedDistroSeries,
    GenerateExtraOverrides,
    )
from lp.archivepublisher.utils import RepositoryIndexFile
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
from lp.services.log.logger import DevNullLogger
from lp.services.osutils import (
    ensure_directory_exists,
    open_for_writing,
    )
from lp.services.scripts.base import LaunchpadScriptFailure
from lp.services.utils import file_exists
from lp.soyuz.enums import PackagePublishingStatus
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
        self.seeddir = self.makeTemporaryDirectory()
        # XXX cjwatson 2011-12-06 bug=694140: Make sure germinate doesn't
        # lose its loggers between tests, due to Launchpad's messing with
        # global log state.
        archive._logger = logging.getLogger("germinate.archive")
        germinator._logger = logging.getLogger("germinate.germinator")
        seeds._logger = logging.getLogger("germinate.seeds")

    def assertFilesEqual(self, expected_path, observed_path):
        self.assertEqual(
            file_contents(expected_path), file_contents(observed_path))

    def makeDistro(self):
        """Create a distribution for testing.

        The distribution will have a root directory set up, which will
        be cleaned up after the test.  It will have an attached archive.
        """
        return self.factory.makeDistribution(
            publish_root_dir=unicode(self.makeTemporaryDirectory()))

    def makeScript(self, distribution, run_setup=True, extra_args=None):
        """Create a script for testing."""
        test_args = []
        if distribution is not None:
            test_args.extend(["-d", distribution.name])
        if extra_args is not None:
            test_args.extend(extra_args)
        script = GenerateExtraOverrides(test_args=test_args)
        script.logger = DevNullLogger()
        script.txn = FakeTransaction()
        if distribution is not None and run_setup:
            script.setUp()
        else:
            script.distribution = distribution
        return script

    def makePackage(self, component, dases, **kwargs):
        """Create a published source and binary package for testing."""
        package = self.factory.makeDistributionSourcePackage(
            distribution=dases[0].distroseries.distribution)
        spph = self.factory.makeSourcePackagePublishingHistory(
            distroseries=dases[0].distroseries,
            pocket=PackagePublishingPocket.RELEASE,
            status=PackagePublishingStatus.PUBLISHED,
            sourcepackagename=package.name, component=component)
        for das in dases:
            build = self.factory.makeBinaryPackageBuild(
                source_package_release=spph.sourcepackagerelease,
                distroarchseries=das, processor=das.default_processor)
            bpr = self.factory.makeBinaryPackageRelease(
                binarypackagename=package.name, build=build,
                component=component, **kwargs)
            lfa = self.factory.makeLibraryFileAlias(
                filename="%s.deb" % package.name)
            transaction.commit()
            bpr.addFile(lfa)
            self.factory.makeBinaryPackagePublishingHistory(
                binarypackagerelease=bpr, distroarchseries=das,
                pocket=PackagePublishingPocket.RELEASE,
                status=PackagePublishingStatus.PUBLISHED)
        return package

    def makeIndexFiles(self, script, distroseries):
        """Create a limited subset of index files for testing."""
        ensure_directory_exists(script.config.temproot)

        for component in distroseries.components:
            index_root = os.path.join(
                script.config.distsroot, distroseries.name, component.name)

            source_index_root = os.path.join(index_root, "source")
            source_index = RepositoryIndexFile(
                source_index_root, script.config.temproot, "Sources")
            for spp in distroseries.getSourcePackagePublishing(
                PackagePublishingStatus.PUBLISHED,
                PackagePublishingPocket.RELEASE, component=component):
                stanza = spp.getIndexStanza().encode("utf-8") + "\n\n"
                source_index.write(stanza)
            source_index.close()

            for arch in distroseries.architectures:
                package_index_root = os.path.join(
                    index_root, "binary-%s" % arch.architecturetag)
                package_index = RepositoryIndexFile(
                    package_index_root, script.config.temproot, "Packages")
                for bpp in distroseries.getBinaryPackagePublishing(
                    archtag=arch.architecturetag,
                    pocket=PackagePublishingPocket.RELEASE,
                    component=component):
                    stanza = bpp.getIndexStanza().encode("utf-8") + "\n\n"
                    package_index.write(stanza)
                package_index.close()

    def composeSeedPath(self, flavour, series_name, seed_name):
        return os.path.join(
            self.seeddir, "%s.%s" % (flavour, series_name), seed_name)

    def makeSeedStructure(self, flavour, series_name, seed_names,
                          seed_inherit=None):
        """Create a simple seed structure file."""
        if seed_inherit is None:
            seed_inherit = {}

        structure_path = self.composeSeedPath(
            flavour, series_name, "STRUCTURE")
        with open_for_writing(structure_path, "w") as structure:
            for seed_name in seed_names:
                inherit = seed_inherit.get(seed_name, [])
                line = "%s: %s" % (seed_name, " ".join(inherit))
                print >>structure, line.strip()

    def makeSeed(self, flavour, series_name, seed_name, entries,
                 headers=None):
        """Create a simple seed file."""
        seed_path = self.composeSeedPath(flavour, series_name, seed_name)
        with open_for_writing(seed_path, "w") as seed:
            if headers is not None:
                for header in headers:
                    print >>seed, header
                print >>seed
            for entry in entries:
                print >>seed, " * %s" % entry

    def getTaskNameFromSeed(self, script, flavour, series_name, seed,
                            primary_flavour):
        """Use script to parse a seed and return its task name."""
        seed_path = self.composeSeedPath(flavour, series_name, seed)
        with open(seed_path) as seed_text:
            task_headers = script.parseTaskHeaders(seed_text)
        return script.getTaskName(
            task_headers, flavour, seed, primary_flavour)

    def getTaskSeedsFromSeed(self, script, flavour, series_name, seed):
        """Use script to parse a seed and return its task seed list."""
        seed_path = self.composeSeedPath(flavour, series_name, seed)
        with open(seed_path) as seed_text:
            task_headers = script.parseTaskHeaders(seed_text)
        return script.getTaskSeeds(task_headers, seed)

    def test_name_is_consistent(self):
        # Script instances for the same distro get the same name.
        distro = self.factory.makeDistribution()
        self.assertEqual(
            GenerateExtraOverrides(test_args=["-d", distro.name]).name,
            GenerateExtraOverrides(test_args=["-d", distro.name]).name)

    def test_name_is_unique_for_each_distro(self):
        # Script instances for different distros get different names.
        self.assertNotEqual(
            GenerateExtraOverrides(
                test_args=["-d", self.factory.makeDistribution().name]).name,
            GenerateExtraOverrides(
                test_args=["-d", self.factory.makeDistribution().name]).name)

    def test_requires_distro(self):
        # The --distribution or -d argument is mandatory.
        script = self.makeScript(None)
        self.assertRaises(OptionValueError, script.processOptions)

    def test_requires_real_distro(self):
        # An incorrect distribution name is flagged as an invalid option
        # value.
        script = self.makeScript(
            None, extra_args=["-d", self.factory.getUniqueString()])
        self.assertRaises(OptionValueError, script.processOptions)

    def test_looks_up_distro(self):
        # The script looks up and keeps the distribution named on the
        # command line.
        distro = self.makeDistro()
        self.factory.makeDistroSeries(distro)
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
        observed_series = [series.name for series in script.series]
        self.assertEqual([development_distroseries.name], observed_series)

    def test_permits_frozen_distro_series(self):
        # If there is no DEVELOPMENT series, a FROZEN one will do.
        distro = self.makeDistro()
        self.factory.makeDistroSeries(distro, status=SeriesStatus.SUPPORTED)
        self.factory.makeDistroSeries(distro, status=SeriesStatus.CURRENT)
        frozen_distroseries = self.factory.makeDistroSeries(
            distro, status=SeriesStatus.FROZEN)
        script = self.makeScript(distro)
        observed_series = [series.name for series in script.series]
        self.assertEqual([frozen_distroseries.name], observed_series)

    def test_requires_development_frozen_distro_series(self):
        # If there is no DEVELOPMENT or FROZEN series, the script fails.
        distro = self.makeDistro()
        self.factory.makeDistroSeries(distro, status=SeriesStatus.SUPPORTED)
        self.factory.makeDistroSeries(distro, status=SeriesStatus.CURRENT)
        script = self.makeScript(distro, run_setup=False)
        self.assertRaises(LaunchpadScriptFailure, script.processOptions)

    def test_multiple_development_frozen_distro_series(self):
        # If there are multiple DEVELOPMENT or FROZEN series, they are all
        # used.
        distro = self.makeDistro()
        development_distroseries_one = self.factory.makeDistroSeries(
            distro, status=SeriesStatus.DEVELOPMENT)
        development_distroseries_two = self.factory.makeDistroSeries(
            distro, status=SeriesStatus.DEVELOPMENT)
        frozen_distroseries_one = self.factory.makeDistroSeries(
            distro, status=SeriesStatus.FROZEN)
        frozen_distroseries_two = self.factory.makeDistroSeries(
            distro, status=SeriesStatus.FROZEN)
        script = self.makeScript(distro)
        expected_series = [
            development_distroseries_one.name,
            development_distroseries_two.name,
            frozen_distroseries_one.name,
            frozen_distroseries_two.name,
            ]
        observed_series = [series.name for series in script.series]
        self.assertContentEqual(expected_series, observed_series)

    def test_components_exclude_partner(self):
        # If a 'partner' component exists, it is excluded.
        distro = self.makeDistro()
        distroseries = self.factory.makeDistroSeries(distro)
        self.factory.makeComponentSelection(
            distroseries=distroseries, component="main")
        self.factory.makeComponentSelection(
            distroseries=distroseries, component="partner")
        script = self.makeScript(distro)
        self.assertEqual(1, len(script.series))
        self.assertEqual(["main"], script.series[0].components)

    def test_compose_output_path_in_germinateroot(self):
        # Output files are written to the correct locations under
        # germinateroot.
        distro = self.makeDistro()
        distroseries = self.factory.makeDistroSeries(distro)
        script = self.makeScript(distro)
        flavour = self.factory.getUniqueString()
        arch = self.factory.getUniqueString()
        base = self.factory.getUniqueString()
        output = script.composeOutputPath(
            flavour, distroseries.name, arch, base)
        self.assertEqual(
            "%s/%s_%s_%s_%s" % (
                script.config.germinateroot, base, flavour, distroseries.name,
                arch),
            output)

    def test_make_seed_structures_missing_seeds(self):
        # makeSeedStructures ignores missing seeds.
        distro = self.makeDistro()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        series_name = distroseries.name
        script = self.makeScript(distro)
        flavour = self.factory.getUniqueString()

        structures = script.makeSeedStructures(
            series_name, [flavour], seed_bases=["file://%s" % self.seeddir])
        self.assertEqual({}, structures)

    def test_make_seed_structures_empty_seed_structure(self):
        # makeSeedStructures ignores an empty seed structure.
        distro = self.makeDistro()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        series_name = distroseries.name
        script = self.makeScript(distro)
        flavour = self.factory.getUniqueString()
        self.makeSeedStructure(flavour, series_name, [])

        structures = script.makeSeedStructures(
            series_name, [flavour], seed_bases=["file://%s" % self.seeddir])
        self.assertEqual({}, structures)

    def test_make_seed_structures_valid_seeds(self):
        # makeSeedStructures reads valid seeds successfully.
        distro = self.makeDistro()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        series_name = distroseries.name
        script = self.makeScript(distro)
        flavour = self.factory.getUniqueString()
        seed = self.factory.getUniqueString()
        self.makeSeedStructure(flavour, series_name, [seed])
        self.makeSeed(flavour, series_name, seed, [])

        structures = script.makeSeedStructures(
            series_name, [flavour], seed_bases=["file://%s" % self.seeddir])
        self.assertIn(flavour, structures)

    def fetchGerminatedOverrides(self, script, distroseries, arch, flavours):
        """Helper to call script.germinateArch and return overrides."""
        structures = script.makeSeedStructures(
            distroseries.name, flavours,
            seed_bases=["file://%s" % self.seeddir])

        override_fd, override_path = tempfile.mkstemp()
        with os.fdopen(override_fd, "w") as override_file:
            script.germinateArch(
                override_file, CachedDistroSeries(distroseries), arch,
                flavours, structures)
        return file_contents(override_path).splitlines()

    def test_germinate_output(self):
        # A single call to germinateArch produces output for all flavours on
        # one architecture.
        distro = self.makeDistro()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        series_name = distroseries.name
        component = self.factory.makeComponent()
        self.factory.makeComponentSelection(
            distroseries=distroseries, component=component)
        das = self.factory.makeDistroArchSeries(distroseries=distroseries)
        arch = das.architecturetag
        one = self.makePackage(component, [das])
        two = self.makePackage(component, [das])
        script = self.makeScript(distro)
        self.makeIndexFiles(script, distroseries)

        flavour_one = self.factory.getUniqueString()
        flavour_two = self.factory.getUniqueString()
        seed = self.factory.getUniqueString()
        self.makeSeedStructure(flavour_one, series_name, [seed])
        self.makeSeed(flavour_one, series_name, seed, [one.name])
        self.makeSeedStructure(flavour_two, series_name, [seed])
        self.makeSeed(flavour_two, series_name, seed, [two.name])

        overrides = self.fetchGerminatedOverrides(
            script, distroseries, arch, [flavour_one, flavour_two])
        self.assertEqual([], overrides)

        seed_dir_one = os.path.join(
            self.seeddir, "%s.%s" % (flavour_one, series_name))
        self.assertFilesEqual(
            os.path.join(seed_dir_one, "STRUCTURE"),
            script.composeOutputPath(
                flavour_one, series_name, arch, "structure"))
        self.assertTrue(file_exists(script.composeOutputPath(
            flavour_one, series_name, arch, "all")))
        self.assertTrue(file_exists(script.composeOutputPath(
            flavour_one, series_name, arch, "all.sources")))
        self.assertTrue(file_exists(script.composeOutputPath(
            flavour_one, series_name, arch, seed)))

        seed_dir_two = os.path.join(
            self.seeddir, "%s.%s" % (flavour_two, series_name))
        self.assertFilesEqual(
            os.path.join(seed_dir_two, "STRUCTURE"),
            script.composeOutputPath(
                flavour_two, series_name, arch, "structure"))
        self.assertTrue(file_exists(script.composeOutputPath(
            flavour_two, series_name, arch, "all")))
        self.assertTrue(file_exists(script.composeOutputPath(
            flavour_two, series_name, arch, "all.sources")))
        self.assertTrue(file_exists(script.composeOutputPath(
            flavour_two, series_name, arch, seed)))

    def test_germinate_output_task(self):
        # germinateArch produces Task extra overrides.
        distro = self.makeDistro()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        series_name = distroseries.name
        component = self.factory.makeComponent()
        self.factory.makeComponentSelection(
            distroseries=distroseries, component=component)
        das = self.factory.makeDistroArchSeries(distroseries=distroseries)
        arch = das.architecturetag
        one = self.makePackage(component, [das])
        two = self.makePackage(component, [das], depends=one.name)
        three = self.makePackage(component, [das])
        self.makePackage(component, [das])
        script = self.makeScript(distro)
        self.makeIndexFiles(script, distroseries)

        flavour = self.factory.getUniqueString()
        seed_one = self.factory.getUniqueString()
        seed_two = self.factory.getUniqueString()
        self.makeSeedStructure(flavour, series_name, [seed_one, seed_two])
        self.makeSeed(
            flavour, series_name, seed_one, [two.name],
            headers=["Task-Description: one"])
        self.makeSeed(
            flavour, series_name, seed_two, [three.name],
            headers=["Task-Description: two"])

        overrides = self.fetchGerminatedOverrides(
            script, distroseries, arch, [flavour])
        expected_overrides = [
            "%s/%s  Task  %s" % (one.name, arch, seed_one),
            "%s/%s  Task  %s" % (two.name, arch, seed_one),
            "%s/%s  Task  %s" % (three.name, arch, seed_two),
            ]
        self.assertContentEqual(expected_overrides, overrides)

    def test_task_name(self):
        # The Task-Name field is honoured.
        series_name = self.factory.getUniqueString()
        package = self.factory.getUniqueString()
        script = self.makeScript(None)

        flavour = self.factory.getUniqueString()
        seed = self.factory.getUniqueString()
        task = self.factory.getUniqueString()
        self.makeSeed(
            flavour, series_name, seed, [package],
            headers=["Task-Name: %s" % task])

        observed_task = self.getTaskNameFromSeed(
            script, flavour, series_name, seed, True)
        self.assertEqual(task, observed_task)

    def test_task_per_derivative(self):
        # The Task-Per-Derivative field is honoured.
        series_name = self.factory.getUniqueString()
        package = self.factory.getUniqueString()
        script = self.makeScript(None)

        flavour_one = self.factory.getUniqueString()
        flavour_two = self.factory.getUniqueString()
        seed_one = self.factory.getUniqueString()
        seed_two = self.factory.getUniqueString()
        self.makeSeed(
            flavour_one, series_name, seed_one, [package],
            headers=["Task-Description: one"])
        self.makeSeed(
            flavour_one, series_name, seed_two, [package],
            headers=["Task-Per-Derivative: 1"])
        self.makeSeed(
            flavour_two, series_name, seed_one, [package],
            headers=["Task-Description: one"])
        self.makeSeed(
            flavour_two, series_name, seed_two, [package],
            headers=["Task-Per-Derivative: 1"])

        observed_task_one_one = self.getTaskNameFromSeed(
            script, flavour_one, series_name, seed_one, True)
        observed_task_one_two = self.getTaskNameFromSeed(
            script, flavour_one, series_name, seed_two, True)
        observed_task_two_one = self.getTaskNameFromSeed(
            script, flavour_two, series_name, seed_one, False)
        observed_task_two_two = self.getTaskNameFromSeed(
            script, flavour_two, series_name, seed_two, False)

        # seed_one is not per-derivative, so it is honoured only for
        # flavour_one and has a global name.
        self.assertEqual(seed_one, observed_task_one_one)
        self.assertIsNone(observed_task_two_one)

        # seed_two is per-derivative, so it is honoured for both flavours
        # and has the flavour name prefixed.
        self.assertEqual(
            "%s-%s" % (flavour_one, seed_two), observed_task_one_two)
        self.assertEqual(
            "%s-%s" % (flavour_two, seed_two), observed_task_two_two)

    def test_task_seeds(self):
        # The Task-Seeds field is honoured.
        series_name = self.factory.getUniqueString()
        one = self.getUniqueString()
        two = self.getUniqueString()
        script = self.makeScript(None)

        flavour = self.factory.getUniqueString()
        seed_one = self.factory.getUniqueString()
        seed_two = self.factory.getUniqueString()
        self.makeSeed(flavour, series_name, seed_one, [one])
        self.makeSeed(
            flavour, series_name, seed_two, [two],
            headers=["Task-Seeds: %s" % seed_one])

        task_seeds = self.getTaskSeedsFromSeed(
            script, flavour, series_name, seed_two)
        self.assertContentEqual([seed_one, seed_two], task_seeds)

    def test_germinate_output_build_essential(self):
        # germinateArch produces Build-Essential extra overrides.
        distro = self.makeDistro()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        series_name = distroseries.name
        component = self.factory.makeComponent()
        self.factory.makeComponentSelection(
            distroseries=distroseries, component=component)
        das = self.factory.makeDistroArchSeries(distroseries=distroseries)
        arch = das.architecturetag
        package = self.makePackage(component, [das])
        script = self.makeScript(distro)
        self.makeIndexFiles(script, distroseries)

        flavour = self.factory.getUniqueString()
        seed = "build-essential"
        self.makeSeedStructure(flavour, series_name, [seed])
        self.makeSeed(flavour, series_name, seed, [package.name])

        overrides = self.fetchGerminatedOverrides(
            script, distroseries, arch, [flavour])
        self.assertContentEqual(
            ["%s/%s  Build-Essential  yes" % (package.name, arch)], overrides)

    def test_process_missing_seeds(self):
        # The script ignores series with no seed structures.
        distro = self.makeDistro()
        distroseries_one = self.factory.makeDistroSeries(distribution=distro)
        distroseries_two = self.factory.makeDistroSeries(distribution=distro)
        component = self.factory.makeComponent()
        self.factory.makeComponentSelection(
            distroseries=distroseries_one, component=component)
        self.factory.makeComponentSelection(
            distroseries=distroseries_two, component=component)
        self.factory.makeDistroArchSeries(distroseries=distroseries_one)
        self.factory.makeDistroArchSeries(distroseries=distroseries_two)
        flavour = self.factory.getUniqueString()
        script = self.makeScript(distro, extra_args=[flavour])
        self.makeIndexFiles(script, distroseries_two)
        seed = self.factory.getUniqueString()
        self.makeSeedStructure(flavour, distroseries_two.name, [seed])
        self.makeSeed(flavour, distroseries_two.name, seed, [])

        script.process(seed_bases=["file://%s" % self.seeddir])
        self.assertFalse(os.path.exists(os.path.join(
            script.config.miscroot,
            "more-extra.override.%s.main" % distroseries_one.name)))
        self.assertTrue(os.path.exists(os.path.join(
            script.config.miscroot,
            "more-extra.override.%s.main" % distroseries_two.name)))

    def test_main(self):
        # If run end-to-end, the script generates override files containing
        # output for all architectures, and sends germinate's log output to
        # a file.
        distro = self.makeDistro()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        series_name = distroseries.name
        component = self.factory.makeComponent()
        self.factory.makeComponentSelection(
            distroseries=distroseries, component=component)
        das_one = self.factory.makeDistroArchSeries(distroseries=distroseries)
        arch_one = das_one.architecturetag
        das_two = self.factory.makeDistroArchSeries(distroseries=distroseries)
        arch_two = das_two.architecturetag
        package = self.makePackage(component, [das_one, das_two])
        flavour = self.factory.getUniqueString()
        script = self.makeScript(distro, extra_args=[flavour])
        self.makeIndexFiles(script, distroseries)

        seed = self.factory.getUniqueString()
        self.makeSeedStructure(flavour, series_name, [seed])
        self.makeSeed(
            flavour, series_name, seed, [package.name],
            headers=["Task-Description: task"])

        script.process(seed_bases=["file://%s" % self.seeddir])
        override_path = os.path.join(
            script.config.miscroot,
            "more-extra.override.%s.main" % series_name)
        expected_overrides = [
            "%s/%s  Task  %s" % (package.name, arch_one, seed),
            "%s/%s  Task  %s" % (package.name, arch_two, seed),
            ]
        self.assertContentEqual(
            expected_overrides, file_contents(override_path).splitlines())

        log_file = os.path.join(
            script.config.germinateroot, "germinate.output")
        self.assertIn("Downloading file://", file_contents(log_file))

    def test_run_script(self):
        # The script will run stand-alone.
        from lp.services.scripts.tests import run_script
        distro = self.makeDistro()
        self.factory.makeDistroSeries(distro)
        transaction.commit()
        retval, out, err = run_script(
            "cronscripts/generate-extra-overrides.py",
            ["-d", distro.name, "-q"])
        self.assertEqual(0, retval)
