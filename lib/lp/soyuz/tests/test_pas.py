# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import os

from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    )
from lp.soyuz.model.processor import ProcessorFamily
from lp.soyuz.pas import (
    BuildDaemonPackagesArchSpecific,
    determineArchitecturesToBuild,
    )
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory
from lp.testing.layers import LaunchpadZopelessLayer


class TestDetermineArchitecturesToBuild(TestCaseWithFactory):
    """Test that determineArchitecturesToBuild correctly interprets hints."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestDetermineArchitecturesToBuild, self).setUp()
        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()
        armel_family = ProcessorFamily.get(5)
        if not armel_family.processors:
            armel_family.addProcessor('armel', 'armel', 'armel')
        self.publisher.breezy_autotest.newArch(
            'armel', armel_family, False, self.publisher.person)
        self.publisher.addFakeChroots()

    def getPASVerifier(self, pas_string):
        """Build and return a PAS verifier based on the string provided."""
        temp_dir = self.makeTemporaryDirectory()
        pas_filename = os.path.join(temp_dir, "Packages-arch-specific")
        with open(pas_filename, "w") as pas_file:
            pas_file.write(pas_string)
        pas_verify = BuildDaemonPackagesArchSpecific(
            temp_dir, self.publisher.breezy_autotest)
        return pas_verify

    def assertArchitecturesToBuild(self, expected_arch_tags, pub,
                                   allowed_arch_tags=None, pas_string=None):
        if allowed_arch_tags is None:
            allowed_archs = self.publisher.breezy_autotest.architectures
        else:
            allowed_archs = [
                arch for arch in self.publisher.breezy_autotest.architectures
                if arch.architecturetag in allowed_arch_tags]
        if pas_string is None:
            pas_verify = None
        else:
            pas_verify = self.getPASVerifier(pas_string)
        architectures = determineArchitecturesToBuild(
            pub, allowed_archs, self.publisher.breezy_autotest,
            pas_verify=pas_verify)
        self.assertContentEqual(
            expected_arch_tags, [a.architecturetag for a in architectures])

    def assertArchsForHint(self, hint_string, expected_arch_tags,
                           allowed_arch_tags=None, sourcename=None,
                           pas_string=None):
        """Assert that the given hint resolves to the expected archtags."""
        pub = self.publisher.getPubSource(
            sourcename=sourcename, architecturehintlist=hint_string)
        self.assertArchitecturesToBuild(
            expected_arch_tags, pub, allowed_arch_tags=allowed_arch_tags,
            pas_string=pas_string)

    def test_single_architecture(self):
        # A hint string with a single arch resolves to just that arch.
        self.assertArchsForHint('hppa', ['hppa'])

    def test_three_architectures(self):
        # A hint string with multiple archs resolves to just those
        # archs.
        self.assertArchsForHint('amd64 i386 hppa', ['hppa', 'i386'])

    def test_independent(self):
        # 'all' is special, meaning just a single build. The
        # nominatedarchindep architecture is used -- in this case i386.
        self.assertArchsForHint('all', ['i386'])

    def test_one_and_independent(self):
        # 'all' is redundant if we have another build anyway.
        self.assertArchsForHint('hppa all', ['hppa'])

    def test_fictional_and_independent(self):
        # But 'all' is useful if present with an arch that wouldn't
        # generate a build.
        self.assertArchsForHint('foo all', ['i386'])

    def test_wildcard(self):
        # 'any' is a wildcard that matches all available archs.
        self.assertArchsForHint('any', ['armel', 'hppa', 'i386'])

    def test_kernel_specific_architecture(self):
        # Since we only support Linux-based architectures, 'linux-foo'
        # is treated the same as 'foo'.
        self.assertArchsForHint('linux-hppa', ['hppa'])

    def test_unknown_kernel_specific_architecture(self):
        # Non-Linux architectures aren't supported.
        self.assertArchsForHint('kfreebsd-hppa', [])

    def test_kernel_wildcard_architecture(self):
        # Wildcards work for kernels: 'any-foo' is treated like 'foo'.
        self.assertArchsForHint('any-hppa', ['hppa'])

    def test_kernel_wildcard_architecture_arm(self):
        # The second part of a wildcard matches the canonical CPU name, not
        # on the Debian architecture, so 'any-arm' matches 'armel'.
        self.assertArchsForHint('any-arm', ['armel'])

    def test_kernel_specific_architecture_wildcard(self):
        # Wildcards work for archs too: 'linux-any' is treated like 'any'.
        self.assertArchsForHint('linux-any', ['armel', 'hppa', 'i386'])

    def test_unknown_kernel_specific_architecture_wildcard(self):
        # But unknown kernels continue to result in nothing.
        self.assertArchsForHint('kfreebsd-any', [])

    def test_wildcard_and_independent(self):
        # 'all' continues to be ignored alongside a valid wildcard.
        self.assertArchsForHint('all linux-any', ['armel', 'hppa', 'i386'])

    def test_kernel_independent_is_invalid(self):
        # 'linux-all' isn't supported.
        self.assertArchsForHint('linux-all', [])

    def test_double_wildcard_is_same_as_single(self):
        # 'any-any' is redundant with 'any', but dpkg-architecture supports
        # it anyway.
        self.assertArchsForHint('any-any', ['armel', 'hppa', 'i386'])

    def test_disabled_architectures_omitted(self):
        # Disabled architectures are not buildable, so are excluded.
        self.publisher.breezy_autotest['hppa'].enabled = False
        self.assertArchsForHint('any', ['armel', 'i386'])

    def test_virtualized_archives_have_only_virtualized_archs(self):
        # For archives which must build on virtual builders, only
        # virtual archs are returned.
        self.publisher.breezy_autotest.main_archive.require_virtualized = True
        self.assertArchsForHint('any', ['i386'])

    def test_no_all_builds_when_nominatedarchindep_not_permitted(self):
        # Some archives (eg. armel rebuilds) don't want arch-indep
        # builds. If the nominatedarchindep architecture (normally
        # i386) is omitted, no builds will be created for arch-indep
        # sources.
        self.assertArchsForHint('all', [], allowed_arch_tags=['hppa'])

    def test_source_pas_defaults_to_all_available_architectures(self):
        # Normally, a source package will be built on all available
        # architectures in the series.
        self.assertArchsForHint(
            "i386 hppa amd64", ["hppa", "i386"], pas_string="")

    def test_source_pas_can_restrict_to_one_architecture(self):
        # A source package can be restricted to a single architecture via PAS.
        self.assertArchsForHint(
            "i386 hppa amd64", ["i386"], sourcename="test",
            pas_string="%test: i386")

    def test_source_pas_can_restrict_to_no_architectures(self):
        # A source package can be restricted to not built on any architecture.
        self.assertArchsForHint(
            "i386 hppa amd64", [], sourcename="test",
            pas_string="%test: sparc")

    def test_source_pas_can_exclude_specific_architecture(self):
        # A source PAS entry can exclude a specific architecture.
        self.assertArchsForHint(
            "i386 hppa amd64", ["hppa"], sourcename="test",
            pas_string="%test: !i386")

    def setUpPPAAndSource(self):
        # Create a PPA and return a new source publication in it.
        archive = self.factory.makeArchive(
            distribution=self.publisher.ubuntutest, purpose=ArchivePurpose.PPA)
        return self.publisher.getPubSource(
            sourcename="test-ppa", architecturehintlist="i386 hppa",
            archive=archive)

    def test_source_pas_does_not_affect_ppa(self):
        # PPA builds are not affected by source PAS restrictions; that is,
        # they will build for all requested architectures currently
        # supported in the PPA subsystem.
        pub_ppa = self.setUpPPAAndSource()
        self.assertArchitecturesToBuild(
            ["i386"], pub_ppa, pas_string="%test-ppa: hppa")
        self.assertArchitecturesToBuild(
            ["i386"], pub_ppa, pas_string="%test-ppa: !i386")

    def setUpSourceAndBinary(self):
        # To check binary PAS listings we'll use a source publication which
        # produces a single binary.
        pub_single = self.publisher.getPubSource(
            sourcename="single", architecturehintlist="any")
        binaries = self.publisher.getPubBinaries(
            binaryname="single-bin", pub_source=pub_single,
            status=PackagePublishingStatus.PUBLISHED)
        binary_names = set(
            pub.binarypackagerelease.name
            for pub in pub_single.getPublishedBinaries())
        self.assertEqual(1, len(binary_names))
        return pub_single, binaries

    def test_binary_pas_unrelated_binary_lines_have_no_effect(self):
        # Source packages are unaffected by an unrelated binary PAS line.
        pub_single, binaries = self.setUpSourceAndBinary()
        self.assertArchitecturesToBuild(
            ["armel", "hppa", "i386"], pub_single, pas_string="boing: i386")

    def test_binary_pas_can_restrict_architectures(self):
        # A PAS entry can restrict the build architectures by tagging the
        # produced binary with a list of allowed architectures.
        pub_single, binaries = self.setUpSourceAndBinary()
        self.assertArchitecturesToBuild(
            ["i386"], pub_single, pas_string="single-bin: i386 sparc")

    def test_binary_pas_can_exclude_specific_architecture(self):
        # A binary PAS entry can exclude a specific architecture.
        pub_single, binaries = self.setUpSourceAndBinary()
        self.assertArchitecturesToBuild(
            ["armel", "i386"], pub_single, pas_string="single-bin: !hppa")

    def test_binary_pas_cannot_exclude_nominatedarchindep(self):
        # A binary PAS entry cannot exclude the 'nominatedarchindep'
        # architecture.  Architecture-independent binaries are only built on
        # nominatedarchindep; if that architecture is blacklisted, those
        # binaries will never be built.
        pub_single, binaries = self.setUpSourceAndBinary()
        self.assertArchitecturesToBuild(
            ["i386"], pub_single, pas_string="single-bin: !i386 !hppa !armel")

    def test_binary_pas_does_not_affect_ppa(self):
        # PPA builds are not affected by binary PAS restrictions.
        pub_ppa = self.setUpPPAAndSource()
        pub_ppa.archive.require_virtualized = False
        self.publisher.getPubBinaries(
            binaryname="ppa-bin", pub_source=pub_ppa,
            status=PackagePublishingStatus.PUBLISHED)
        self.assertArchitecturesToBuild(
            ["hppa", "i386"], pub_ppa, pas_string="")
        self.assertArchitecturesToBuild(
            ["hppa", "i386"], pub_ppa, pas_string="ppa-bin: !hppa")

    def test_binary_pas_does_not_affect_multi_binary_sources(self):
        # Binary PAS entries referring to binary packages whose source
        # produces other binaries are completely ignored.  Other tools use
        # that information, but we can't restrict builds in this
        # circumstance.
        pub_multiple = self.publisher.getPubSource(
            sourcename="multiple", architecturehintlist="any")
        for build in pub_multiple.createMissingBuilds():
            bin_one = self.publisher.uploadBinaryForBuild(build, "bin-one")
            self.publisher.publishBinaryInArchive(
                bin_one, pub_multiple.archive,
                status=PackagePublishingStatus.PUBLISHED)
            bin_two = self.publisher.uploadBinaryForBuild(build, "bin-two")
            self.publisher.publishBinaryInArchive(
                bin_two, pub_multiple.archive,
                status=PackagePublishingStatus.PUBLISHED)
        binary_names = set(
            pub.binarypackagerelease.name
            for pub in pub_multiple.getPublishedBinaries())
        self.assertEqual(2, len(binary_names))
        self.assertArchitecturesToBuild(
            ["armel", "hppa", "i386"], pub_multiple, pas_string="")
        self.assertArchitecturesToBuild(
            ["armel", "hppa", "i386"], pub_multiple,
            pas_string="bin-one: i386 sparc")
        self.assertArchitecturesToBuild(
            ["armel", "hppa", "i386"], pub_multiple,
            pas_string="bin-two: !hppa")
