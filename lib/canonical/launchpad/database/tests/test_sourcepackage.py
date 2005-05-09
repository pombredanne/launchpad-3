
# Test suite for the SourcePackage classes

# Copyright (c) 2005 Canonical Ltd

import sys
import unittest, doctest
import warnings

class ZopelessTestCase(unittest.TestCase):
    """Base class for test cases that need database access."""

    def setUp(self):
        from canonical.launchpad.ftests import harness
        harness.LaunchpadZopelessTestSetup().setUp()

    def tearDown(self):
        from canonical.launchpad.ftests import harness
        harness.LaunchpadZopelessTestSetup().tearDown()


class PackagingDiscoveryTestCase(ZopelessTestCase):
    """Make sure we can make a good guess at the productseries for a source
    package, based on the packaging data and some heuristics."""

    def setUp(self):
        ZopelessTestCase.setUp(self)
        from canonical.launchpad.database import SourcePackageName, \
                DistroRelease, SourcePackage
        # source package names
        self.evolution = SourcePackageName.byName('evolution')
        self.a52dec = SourcePackageName.byName('a52dec')
        self.netapplet = SourcePackageName.byName('netapplet')
        self.firefox = SourcePackageName.byName('mozilla-firefox')
        # distroreleases
        self.warty = DistroRelease.get(1)
        self.hoary = DistroRelease.get(3)
        self.sarge = DistroRelease.get(7)
        self.sid = DistroRelease.get(8)
        self.g2k5 = DistroRelease.get(9)

    def testDirectPackagingData(self):
        "We get the productseries when it is directly given in Packaging"

        from canonical.launchpad.database import SourcePackage
        sp = SourcePackage(sourcepackagename=self.firefox,
                           distrorelease=self.hoary)
        self.assertEqual(sp.productseries.name, '1.0')

    def testPreviousUbuntuPackagingData(self):
        "We get the productseries from a previous ubuntu package"

        # first make sure there is no Packaging entry for a52dec in hoary
        from canonical.launchpad.database import Packaging
        from canonical.launchpad.database import SourcePackage
        self.assertEqual(Packaging.selectBy(
                            sourcepackagenameID=self.a52dec.id,
                            distroreleaseID=self.hoary.id).count(), 0)
        # now verify we still get a product for that sp
        sp = SourcePackage(sourcepackagename=self.a52dec,
                           distrorelease=self.hoary)
        self.assertEqual(sp.productseries.product.name, 'a52dec')

    def testParentReleasePackaging(self):
        "We get the productseries from the parent release if needed"
        # first make sure there is no Packaging entry for a52dec in g2k5
        from canonical.launchpad.database import Packaging
        from canonical.launchpad.database import SourcePackage
        self.assertEqual(Packaging.selectBy(
                sourcepackagenameID=self.a52dec.id,
                distroreleaseID=self.g2k5.id).count(), 0)
        # now verify we still get a product for that sp
        sp = SourcePackage(sourcepackagename=self.a52dec,
                           distrorelease=self.g2k5)
        self.assertEqual(sp.productseries.product.name, 'a52dec')


def test_suite():
    '''return all the tests in this module'''
    loader=unittest.TestLoader()
    loader.suiteClass=unittest.TestSuite
    return loader.loadTestsFromName(__name__)

def main(argv):
    suite = unittest.TestLoader().loadTestsFromName(__name__)
    runner=unittest.TextTestRunner(verbosity=2)
    #threadTest(lambda: runner.run(suite))
    #if not runner.wasSuccessful(): return 1
    result = runner.run(suite)
    if not result.wasSuccessful(): return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

