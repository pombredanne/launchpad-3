import unittest
from canonical.launchpad.ftests.harness import LaunchpadFunctionalTestCase
from canonical.lp.placelessauth.encryption import SSHADigestEncryptor
from canonical.lp.placelessauth.launchpadsourceutility import \
     LaunchpadLoginSource
from canonical.lp.placelessauth.interfaces import IPlacelessLoginSource
from zope.app.tests import ztapi
from zope.app import zapi
from zope.app.tests.placelesssetup import PlacelessSetup

class TestLaunchpadLoginSource(LaunchpadFunctionalTestCase):

    def setUp(self):
        super(TestLaunchpadLoginSource, self).setUp()
        source = LaunchpadLoginSource()
        ztapi.provideUtility(IPlacelessLoginSource, source, 'fleeb')

    def tearDown(self):
        ztapi.unprovideUtility(IPlacelessLoginSource, 'fleeb')
        super(TestLaunchpadLoginSource, self).tearDown()

    def testAPI(self):

        # Put all of this in a single test function so we can
        # set up the database easily and only once
        # All this assumes data from the static launchpad_unittest data
        utility = zapi.getUtility(IPlacelessLoginSource, 'fleeb')

        # test_getPrincipal
        self.assertEqual(utility.getPrincipal(1).id, 1)

        # test_getPrincipals
        self.assertEqual(
            [ x.id for x in utility.getPrincipals('obert') ], [2]
            )
        self.assertEqual(
            [ x.id for x in utility.getPrincipals('mark') ], [1]
            )

        # test_getPrincipalByLogin
        self.assertEqual(utility.getPrincipalByLogin('mark@hbd.com').id, 1)
        self.assertEqual(utility.getPrincipalByLogin('ass'), None)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestLaunchpadLoginSource))
    return suite

if __name__ == '__main__':
    unittest.main()

