# Copyright 2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test archive dependencies."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from testtools.matchers import StartsWith
import transaction
from zope.component import getUtility

from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.log.logger import BufferLogger
from lp.soyuz.adapters.archivedependencies import (
    default_component_dependency_name,
    default_pocket_dependency,
    get_components_for_context,
    get_primary_current_component,
    get_sources_list_for_building,
    pocket_dependencies,
    )
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.interfaces.archive import IArchive
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory
from lp.testing.layers import (
    LaunchpadZopelessLayer,
    ZopelessDatabaseLayer,
    )


class TestOgreModel(TestCaseWithFactory):
    """Test ogre-model component handling.

    The Ubuntu "ogre model" (cf. Shrek) ensures that build-dependencies are
    consistent with the component in which the source is published.
    """

    layer = ZopelessDatabaseLayer

    def setUpComponents(self, distroseries, component_names):
        for component_name in component_names:
            component = getUtility(IComponentSet)[component_name]
            self.factory.makeComponentSelection(distroseries, component)

    def assertComponentMap(self, expected, distroseries, pocket):
        for component_name, expected_components in expected.items():
            component = getUtility(IComponentSet)[component_name]
            self.assertEqual(
                expected_components,
                get_components_for_context(component, distroseries, pocket))

    def test_strict_supported_component_dependencies(self):
        # In strict-supported-component-dependencies mode, a source
        # published in main is only allowed to build-depend on binaries also
        # published in main, while a source published in universe is allowed
        # to build-depend on main and universe.
        distroseries = self.factory.makeDistroSeries()
        expected = {
            "main": ["main"],
            "restricted": ["main", "restricted"],
            "universe": ["main", "universe"],
            "multiverse": ["main", "restricted", "universe", "multiverse"],
            "partner": ["partner"],
            }
        self.setUpComponents(distroseries, expected.keys())
        self.assertComponentMap(
            expected, distroseries, PackagePublishingPocket.RELEASE)

    def test_lax_supported_component_dependencies(self):
        # In lax-supported-component-dependencies mode, source packages in
        # "supported" components (main and restricted) may additionally
        # build-depend on binary packages in "unsupported" components
        # (universe and multiverse).
        distroseries = self.factory.makeDistroSeries()
        distroseries.strict_supported_component_dependencies = False
        expected = {
            "main": ["main", "universe"],
            "restricted": ["main", "restricted", "universe", "multiverse"],
            "universe": ["main", "universe"],
            "multiverse": ["main", "restricted", "universe", "multiverse"],
            "partner": ["partner"],
            }
        self.setUpComponents(distroseries, expected.keys())
        self.assertComponentMap(
            expected, distroseries, PackagePublishingPocket.RELEASE)

    def test_backports(self):
        # Source packages in the BACKPORTS pocket are allowed to
        # build-depend on binary packages in any component.  This avoids
        # having to make potentially-invasive changes to accommodate
        # backporting to stable series.
        distroseries = self.factory.makeDistroSeries()
        expected = {
            "main": ["main", "restricted", "universe", "multiverse"],
            "restricted": ["main", "restricted", "universe", "multiverse"],
            "universe": ["main", "restricted", "universe", "multiverse"],
            "multiverse": ["main", "restricted", "universe", "multiverse"],
            "partner": ["main", "restricted", "universe", "multiverse"],
            }
        self.setUpComponents(distroseries, expected.keys())
        self.assertComponentMap(
            expected, distroseries, PackagePublishingPocket.BACKPORTS)


class TestSourcesList(TestCaseWithFactory):
    """Test sources.list contents for building, and related mechanisms."""

    layer = LaunchpadZopelessLayer

    ubuntu_components = [
        "main", "restricted", "universe", "multiverse", "partner"]

    def setUp(self):
        super(TestSourcesList, self).setUp()
        self.publisher = SoyuzTestPublisher()
        self.ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
        self.hoary = self.ubuntu.getSeries("hoary")
        self.publisher.addFakeChroots(self.hoary)
        self.publisher.setUpDefaultDistroSeries(self.hoary)
        for component_name in self.ubuntu_components:
            component = getUtility(IComponentSet)[component_name]
            if component not in self.hoary.components:
                self.factory.makeComponentSelection(self.hoary, component)

    def test_defaults(self):
        # Non-primary archives by default use the Release, Security and
        # Updates pockets from the primary archive, and all its available
        # components.
        self.assertEqual(
            PackagePublishingPocket.UPDATES, default_pocket_dependency)
        self.assertEqual("multiverse", default_component_dependency_name)
        self.assertEqual(
            (PackagePublishingPocket.RELEASE,
             PackagePublishingPocket.SECURITY,
             PackagePublishingPocket.UPDATES),
            pocket_dependencies[default_pocket_dependency])

    def makeArchive(self, publish_binary=False, **kwargs):
        archive = self.factory.makeArchive(distribution=self.ubuntu, **kwargs)
        if publish_binary:
            self.publisher.getPubBinaries(
                archive=archive, status=PackagePublishingStatus.PUBLISHED)
        return archive

    def makeBuild(self, **kwargs):
        pub_source = self.publisher.getPubSource(**kwargs)
        [build] = pub_source.createMissingBuilds()
        return build

    def assertPrimaryCurrentComponent(self, expected, build):
        self.assertEqual(
            expected,
            get_primary_current_component(
                build.archive, build.distro_series,
                build.source_package_release.name).name)

    def assertSourcesList(self, expected, build, **kwargs):
        expected_lines = []
        for archive_or_prefix, suffixes in expected:
            if IArchive.providedBy(archive_or_prefix):
                prefix = "deb %s " % archive_or_prefix.archive_url
            else:
                prefix = archive_or_prefix + " "
            expected_lines.extend([prefix + suffix for suffix in suffixes])
        sources_list = get_sources_list_for_building(
            build, build.distro_arch_series, build.source_package_release.name,
            **kwargs)
        self.assertEqual(expected_lines, sources_list)

    def test_ppa_with_no_binaries(self):
        # If there are no published binaries in a PPA, only its primary
        # archive dependencies need to be considered.
        ppa = self.makeArchive()
        build = self.makeBuild(archive=ppa)
        self.assertEqual(
            0, ppa.getAllPublishedBinaries(
                distroarchseries=build.distro_arch_series,
                status=PackagePublishingStatus.PUBLISHED).count())
        self.assertSourcesList(
            [(self.ubuntu.main_archive, [
                 "hoary main restricted universe multiverse",
                 "hoary-security main restricted universe multiverse",
                 "hoary-updates main restricted universe multiverse",
                 ]),
             ], build)

    def test_ppa_with_binaries(self):
        # If there are binaries published in a PPA, then the PPA is
        # considered as well as its primary dependencies.
        ppa = self.makeArchive(publish_binary=True)
        build = self.makeBuild(archive=ppa)
        self.assertSourcesList(
            [(ppa, ["hoary main"]),
             (self.ubuntu.main_archive, [
                 "hoary main restricted universe multiverse",
                 "hoary-security main restricted universe multiverse",
                 "hoary-updates main restricted universe multiverse",
                 ]),
             ], build)

    def test_dependent_ppa_with_no_binaries(self):
        # A depended-upon PPA is not considered if it has no published
        # binaries.
        lower_ppa = self.makeArchive()
        upper_ppa = self.makeArchive(publish_binary=True)
        upper_ppa.addArchiveDependency(
            lower_ppa, PackagePublishingPocket.RELEASE,
            getUtility(IComponentSet)["main"])
        build = self.makeBuild(archive=upper_ppa)
        self.assertSourcesList(
            [(upper_ppa, ["hoary main"]),
             (self.ubuntu.main_archive, [
                 "hoary main restricted universe multiverse",
                 "hoary-security main restricted universe multiverse",
                 "hoary-updates main restricted universe multiverse",
                 ]),
             ], build)

    def test_dependent_ppa_with_binaries(self):
        # A depended-upon PPA is considered if it has published binaries.
        lower_ppa = self.makeArchive(publish_binary=True)
        upper_ppa = self.makeArchive(publish_binary=True)
        upper_ppa.addArchiveDependency(
            lower_ppa, PackagePublishingPocket.RELEASE,
            getUtility(IComponentSet)["main"])
        build = self.makeBuild(archive=upper_ppa)
        self.assertSourcesList(
            [(upper_ppa, ["hoary main"]),
             (lower_ppa, ["hoary main"]),
             (self.ubuntu.main_archive, [
                 "hoary main restricted universe multiverse",
                 "hoary-security main restricted universe multiverse",
                 "hoary-updates main restricted universe multiverse",
                 ]),
             ], build)

    def test_lax_supported_component_dependencies(self):
        # Dependencies for series with
        # strict_supported_component_dependencies=False are reasonable.
        # PPAs only have the "main" component.
        lower_ppa = self.makeArchive(publish_binary=True)
        upper_ppa = self.makeArchive(publish_binary=True)
        upper_ppa.addArchiveDependency(
            lower_ppa, PackagePublishingPocket.RELEASE,
            getUtility(IComponentSet)["main"])
        upper_ppa.addArchiveDependency(
            self.ubuntu.main_archive, PackagePublishingPocket.UPDATES,
            getUtility(IComponentSet)["restricted"])
        build = self.makeBuild(archive=upper_ppa)
        self.assertSourcesList(
            [(upper_ppa, ["hoary main"]),
             (lower_ppa, ["hoary main"]),
             (self.ubuntu.main_archive, [
                 "hoary main restricted",
                 "hoary-security main restricted",
                 "hoary-updates main restricted",
                 ]),
             ], build)
        self.hoary.strict_supported_component_dependencies = False
        transaction.commit()
        self.assertSourcesList(
            [(upper_ppa, ["hoary main"]),
             (lower_ppa, ["hoary main"]),
             (self.ubuntu.main_archive, [
                 "hoary main restricted universe multiverse",
                 "hoary-security main restricted universe multiverse",
                 "hoary-updates main restricted universe multiverse",
                 ]),
             ], build)

    def test_no_op_primary_archive_dependency(self):
        # Overriding the default primary archive dependencies with exactly
        # the same values has no effect.
        ppa = self.makeArchive()
        ppa.addArchiveDependency(
            self.ubuntu.main_archive, PackagePublishingPocket.UPDATES,
            getUtility(IComponentSet)["multiverse"])
        build = self.makeBuild(archive=ppa)
        self.assertSourcesList(
            [(self.ubuntu.main_archive, [
                 "hoary main restricted universe multiverse",
                 "hoary-security main restricted universe multiverse",
                 "hoary-updates main restricted universe multiverse",
                 ]),
             ], build)

    def test_primary_archive_dependency_security(self):
        # The primary archive dependency can be modified to behave as an
        # embargoed archive that builds security updates.  This is done by
        # setting the SECURITY pocket dependencies (RELEASE and SECURITY)
        # and following the component dependencies of the component where
        # the source was last published in the primary archive.
        ppa = self.makeArchive()
        ppa.addArchiveDependency(
            self.ubuntu.main_archive, PackagePublishingPocket.SECURITY)
        build = self.makeBuild(archive=ppa)
        self.assertPrimaryCurrentComponent("universe", build)
        self.assertSourcesList(
            [(self.ubuntu.main_archive, [
                 "hoary main universe",
                 "hoary-security main universe",
                 ]),
             ], build)
        self.publisher.getPubSource(
            sourcename="with-ancestry", version="1.0",
            archive=self.ubuntu.main_archive)
        [build_with_ancestry] = self.publisher.getPubSource(
            sourcename="with-ancestry", version="1.1",
            archive=ppa).createMissingBuilds()
        self.assertPrimaryCurrentComponent("main", build_with_ancestry)
        self.assertSourcesList(
            [(self.ubuntu.main_archive, [
                 "hoary main",
                 "hoary-security main",
                 ]),
             ], build_with_ancestry)

    def test_primary_archive_dependency_release(self):
        # The primary archive dependency can be modified to behave as a
        # pristine build environment based only on what was included in the
        # original release of the corresponding series.
        ppa = self.makeArchive()
        ppa.addArchiveDependency(
            self.ubuntu.main_archive, PackagePublishingPocket.RELEASE,
            getUtility(IComponentSet)["restricted"])
        build = self.makeBuild(archive=ppa)
        self.assertSourcesList(
            [(self.ubuntu.main_archive, ["hoary main restricted"])], build)

    def test_primary_archive_dependency_proposed(self):
        # The primary archive dependency can be modified to extend the build
        # environment for PROPOSED.
        ppa = self.makeArchive()
        ppa.addArchiveDependency(
            self.ubuntu.main_archive, PackagePublishingPocket.PROPOSED,
            getUtility(IComponentSet)["multiverse"])
        build = self.makeBuild(archive=ppa)
        self.assertSourcesList(
            [(self.ubuntu.main_archive, [
                 "hoary main restricted universe multiverse",
                 "hoary-security main restricted universe multiverse",
                 "hoary-updates main restricted universe multiverse",
                 "hoary-proposed main restricted universe multiverse",
                 ]),
             ], build)

    def test_primary_archive_dependency_backports(self):
        # The primary archive dependency can be modified to extend the build
        # environment for PROPOSED.
        ppa = self.makeArchive()
        ppa.addArchiveDependency(
            self.ubuntu.main_archive, PackagePublishingPocket.BACKPORTS,
            getUtility(IComponentSet)["multiverse"])
        build = self.makeBuild(archive=ppa)
        self.assertSourcesList(
            [(self.ubuntu.main_archive, [
                 "hoary main restricted universe multiverse",
                 "hoary-security main restricted universe multiverse",
                 "hoary-updates main restricted universe multiverse",
                 "hoary-backports main restricted universe multiverse",
                 ]),
             ], build)

    def test_partner(self):
        # Similarly to what happens with PPA builds, partner builds may
        # depend on any component in the primary archive.  This behaviour
        # allows scenarios where partner packages may use other
        # restricted/non-free applications from multiverse, and also other
        # partner applications.
        primary, partner = self.ubuntu.all_distro_archives
        self.publisher.getPubBinaries(
            archive=partner, component="partner",
            status=PackagePublishingStatus.PUBLISHED)
        build = self.makeBuild(archive=partner, component="partner")
        self.assertSourcesList(
            [(partner, ["hoary partner"]),
             (primary, [
                 "hoary main restricted universe multiverse",
                 "hoary-security main restricted universe multiverse",
                 "hoary-updates main restricted universe multiverse",
                 ]),
             ], build)

    def test_partner_proposed(self):
        # The partner archive's PROPOSED pocket builds against itself, but
        # still uses the default UPDATES dependency for the primary archive
        # unless overridden by ArchiveDependency.
        primary, partner = self.ubuntu.all_distro_archives
        self.publisher.getPubBinaries(
            archive=partner, component="partner",
            status=PackagePublishingStatus.PUBLISHED)
        self.publisher.getPubBinaries(
            archive=partner, component="partner",
            status=PackagePublishingStatus.PUBLISHED,
            pocket=PackagePublishingPocket.PROPOSED)
        build = self.makeBuild(
            archive=partner, component="partner",
            pocket=PackagePublishingPocket.PROPOSED)
        self.assertSourcesList(
            [(partner, [
                 "hoary partner",
                 "hoary-proposed partner",
                 ]),
             (primary, [
                 "hoary main restricted universe multiverse",
                 "hoary-security main restricted universe multiverse",
                 "hoary-updates main restricted universe multiverse",
                 ]),
             ], build)

    def test_archive_external_dependencies(self):
        # An archive can be manually given additional external dependencies.
        # If present, "%(series)s" is replaced with the series name for the
        # build being dispatched.
        ppa = self.makeArchive(publish_binary=True)
        ppa.external_dependencies = (
            "deb http://user:pass@repository zoing everything\n"
            "deb http://user:pass@repository %(series)s public private\n"
            "deb http://user:pass@repository %(series)s-extra public")
        build = self.makeBuild(archive=ppa)
        self.assertSourcesList(
            [(ppa, ["hoary main"]),
             ("deb http://user:pass@repository", [
                 "zoing everything",
                 "hoary public private",
                 "hoary-extra public",
                 ]),
             (self.ubuntu.main_archive, [
                 "hoary main restricted universe multiverse",
                 "hoary-security main restricted universe multiverse",
                 "hoary-updates main restricted universe multiverse",
                 ]),
             ], build)

    def test_build_external_dependencies(self):
        # A single build can be manually given additional external
        # dependencies.
        ppa = self.makeArchive(publish_binary=True)
        build = self.makeBuild(archive=ppa)
        build.api_external_dependencies = (
            "deb http://user:pass@repository foo bar")
        self.assertSourcesList(
            [(ppa, ["hoary main"]),
             ("deb http://user:pass@repository", ["foo bar"]),
             (self.ubuntu.main_archive, [
                 "hoary main restricted universe multiverse",
                 "hoary-security main restricted universe multiverse",
                 "hoary-updates main restricted universe multiverse",
                 ]),
             ], build)

    def test_build_tools(self):
        # We can force an extra build tools line to be added to
        # sources.list, which is useful for specialised build types.
        ppa = self.makeArchive(publish_binary=True)
        build = self.makeBuild(archive=ppa)
        self.assertSourcesList(
            [(ppa, ["hoary main"]),
             ("deb http://example.org", ["hoary main"]),
             (self.ubuntu.main_archive, [
                 "hoary main restricted universe multiverse",
                 "hoary-security main restricted universe multiverse",
                 "hoary-updates main restricted universe multiverse",
                 ]),
             ], build, tools_source="deb http://example.org %(series)s main")

    def test_build_tools_bad_formatting(self):
        # If tools_source is badly formatted, we log the error but don't
        # blow up.  (Note the missing "s" at the end of "%(series)".)
        ppa = self.makeArchive(publish_binary=True)
        build = self.makeBuild(archive=ppa)
        logger = BufferLogger()
        self.assertSourcesList(
            [(ppa, ["hoary main"]),
             (self.ubuntu.main_archive, [
                 "hoary main restricted universe multiverse",
                 "hoary-security main restricted universe multiverse",
                 "hoary-updates main restricted universe multiverse",
                 ]),
             ],
            build, tools_source="deb http://example.org %(series) main",
            logger=logger)
        self.assertThat(logger.getLogBuffer(), StartsWith(
            "ERROR Exception processing build tools sources.list entry:\n"))

    def test_overlay(self):
        # An overlay distroseries is a derived distribution which works like
        # a PPA.  This means that the parent's details gets added to the
        # sources.list passed to the builders.
        depdistro = self.factory.makeDistribution(
            "depdistro", publish_base_url="http://archive.launchpad.dev/")
        depseries = self.factory.makeDistroSeries(
            distribution=depdistro, name="depseries")
        self.factory.makeDistroArchSeries(
            distroseries=depseries, architecturetag="i386")
        self.publisher.addFakeChroots(depseries)
        for component_name in self.ubuntu_components:
            component = getUtility(IComponentSet)[component_name]
            self.factory.makeComponentSelection(depseries, component)
        self.factory.makeDistroSeriesParent(
            derived_series=self.hoary, parent_series=depseries,
            initialized=True, is_overlay=True,
            pocket=PackagePublishingPocket.SECURITY,
            component=getUtility(IComponentSet)["universe"])
        build = self.makeBuild()
        self.assertSourcesList(
            [(self.ubuntu.main_archive, ["hoary main"]),
             (depdistro.main_archive, [
                 "depseries main universe",
                 "depseries-security main universe",
                 ]),
             ], build)
