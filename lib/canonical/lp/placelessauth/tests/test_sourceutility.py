import unittest
from zope.app.tests.placelesssetup import PlacelessSetup
from zope.app.pluggableauth import SimplePrincipal
from canonical.lp.placelessauth.interfaces import IPlacelessLoginSource
from canonical.lp.placelessauth.sourceutility import PlacelessLoginSource
from zope.app.tests import ztapi
from zope.app import zapi

class Nothing:
    pass

class TestSourceUtility(PlacelessSetup, unittest.TestCase):

    def setUp(self):
        PlacelessSetup.setUp(self)

        source = PlacelessLoginSource()
        
        self.user = SimplePrincipal('user1', '123', 'gams', 'gust')
        source['user1'] = self.user
        ztapi.provideUtility(IPlacelessLoginSource, source)

    def test_getPrincipal(self):
        source = zapi.getUtility(IPlacelessLoginSource)
        self.assertEqual(source.getPrincipal(self.user.id), self.user)

    def test_getPrincipals(self):
        source = zapi.getUtility(IPlacelessLoginSource)
        self.assertEqual(list(source.getPrincipals('user1')), [self.user])

    def test_getPrincipalByLogin(self):
        source = zapi.getUtility(IPlacelessLoginSource)
        self.assertEqual(source.getPrincipalByLogin('user1'), self.user)

def test_suite():
    t = unittest.makeSuite(TestSourceUtility)
    return unittest.TestSuite((t,))

if __name__=='__main__':
    main(defaultTest='test_suite')
