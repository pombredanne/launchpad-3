# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from canonical.testing.layers import LaunchpadZopelessLayer
from lp.soyuz.pas import determineArchitecturesToBuild
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory


class TestDetermineArchitecturesToBuild(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestDetermineArchitecturesToBuild, self).setUp()
        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()
        self.publisher.addFakeChroots()

    def assertArchsForHint(self, hint_string, expected_arch_tags):
        pub = self.publisher.getPubSource(architecturehintlist=hint_string)
        architectures = determineArchitecturesToBuild(
            pub, self.publisher.breezy_autotest.architectures,
            self.publisher.breezy_autotest)
        self.assertEqual(
            expected_arch_tags, [a.architecturetag for a in architectures])

    def testSingleArchitecture(self):
        self.assertArchsForHint('hppa', ['hppa'])

    def testThreeArchitectures(self):
        self.assertArchsForHint('amd64 i386 hppa', ['hppa', 'i386'])

    def testIndependent(self):
        self.assertArchsForHint('all', ['i386'])

    def testOneAndIndependent(self):
        self.assertArchsForHint('hppa all', ['hppa'])

    def testFictionalAndIndependent(self):
        self.assertArchsForHint('foo all', ['i386'])

    def testWildcard(self):
        self.assertArchsForHint('any', ['hppa', 'i386'])

    def testKernelSpecificArchitecture(self):
        self.assertArchsForHint('linux-hppa', ['hppa'])

    def testKernelWildcardArchitecture(self):
        self.assertArchsForHint('any-hppa', ['hppa'])

    def testKernelSpecificArchitectureWildcard(self):
        self.assertArchsForHint('linux-any', ['hppa', 'i386'])

    def testWildcardAndIndependent(self):
        self.assertArchsForHint('all linux-any', ['hppa', 'i386'])

    def testKernelIndependentIsInvalid(self):
        self.assertArchsForHint('linux-all', [])

    def testDoubleWildcardIsInvalid(self):
        self.assertArchsForHint('any-any', [])

    def testDisabledArchitecturesOmitted(self):
        self.publisher.breezy_autotest['hppa'].enabled = False
        self.assertArchsForHint('any', ['i386'])
