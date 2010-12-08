# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from canonical.testing.layers import LaunchpadZopelessLayer
from lp.soyuz.pas import determineArchitecturesToBuild
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory


class TestDetermineArchitecturesToBuild(TestCaseWithFactory):
    """Test that determineArchitecturesToBuild correctly interprets hints."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestDetermineArchitecturesToBuild, self).setUp()
        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()
        self.publisher.addFakeChroots()

    def assertArchsForHint(self, hint_string, expected_arch_tags):
        """Assert that the given hint resolves to the expected archtags."""
        pub = self.publisher.getPubSource(architecturehintlist=hint_string)
        architectures = determineArchitecturesToBuild(
            pub, self.publisher.breezy_autotest.architectures,
            self.publisher.breezy_autotest)
        self.assertEqual(
            expected_arch_tags, [a.architecturetag for a in architectures])

    def testSingleArchitecture(self):
        # A hint string with a single arch resolves to just that arch.
        self.assertArchsForHint('hppa', ['hppa'])

    def testThreeArchitectures(self):
        # A hint string with multiple archs resolves to just those
        # archs.
        self.assertArchsForHint('amd64 i386 hppa', ['hppa', 'i386'])

    def testIndependent(self):
        # 'all' is special, meaning just a single build. The
        # nominatedarchindep architecture is used -- in this case i386.
        self.assertArchsForHint('all', ['i386'])

    def testOneAndIndependent(self):
        # 'all' is redundant if we have another build anyway.
        self.assertArchsForHint('hppa all', ['hppa'])

    def testFictionalAndIndependent(self):
        # But 'all' is useful if present with an arch that wouldn't
        # generate a build.
        self.assertArchsForHint('foo all', ['i386'])

    def testWildcard(self):
        # 'any' is a wildcard that matches all available archs.
        self.assertArchsForHint('any', ['hppa', 'i386'])

    def testKernelSpecificArchitecture(self):
        # Since we only support Linux-based architectures, 'linux-foo'
        # is treated the same as 'foo'.
        self.assertArchsForHint('linux-hppa', ['hppa'])

    def testUnknownKernelSpecificArchitecture(self):
        # Non-Linux architectures aren't supported.
        self.assertArchsForHint('kfreebsd-hppa', [])

    def testKernelWildcardArchitecture(self):
        # Wildcards work for kernels: 'any-foo' is treated like 'foo'.
        self.assertArchsForHint('any-hppa', ['hppa'])

    def testKernelSpecificArchitectureWildcard(self):
        # Wildcards work for archs too: 'linux-any' is treated like 'any'.
        self.assertArchsForHint('linux-any', ['hppa', 'i386'])

    def testUnknownKernelSpecificArchitectureWildcard(self):
        # But unknown kernels continue to result in nothing.
        self.assertArchsForHint('kfreebsd-any', [])

    def testWildcardAndIndependent(self):
        # 'all' continues to be ignored alongside a valid wildcard.
        self.assertArchsForHint('all linux-any', ['hppa', 'i386'])

    def testKernelIndependentIsInvalid(self):
        # 'linux-all' isn't supported.
        self.assertArchsForHint('linux-all', [])

    def testDoubleWildcardIsInvalid(self):
        # 'any-any' is invalid; you want 'any'.
        self.assertArchsForHint('any-any', [])

    def testDisabledArchitecturesOmitted(self):
        # Disabled architectures are not buildable, so are excluded.
        self.publisher.breezy_autotest['hppa'].enabled = False
        self.assertArchsForHint('any', ['i386'])

    def testVirtualizedArchivesHaveOnlyVirtualizedArchs(self):
        # For archives which must build on virtual builders, only
        # virtual archs are returned.
        self.publisher.breezy_autotest.main_archive.require_virtualized = True
        self.assertArchsForHint('any', ['i386'])
