import unittest
from zope.app import zapi
from harness import LaunchpadTestCase, LaunchpadFunctionalTestCase

class TestLaunchpadTestCase(LaunchpadTestCase):
    def test_sampledata(self):
        con = self.connect()
        cur = con.cursor()
        cur.execute("""
            select count(*) from person 
            where displayname='mark shuttleworth'
            """)
        r = cur.fetchone()
        self.failunlessequal(r[0], 1, 'sample data not loaded')
        cur.close()
        con.close()

class TestLaunchpadFunctionalTestCase(LaunchpadFunctionalTestCase):
    test_database = TestLaunchpadTestCase.test_sampledata

    def test_placeless(self):
        # Do something that requires functional machinery loaded
        zapi.getUtility(IMailer, 'smtp')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestLaunchpadTestCase))
    suite.addTest(unittest.makeSuite(TestLaunchpadFunctionalTestCase))
    return None

if __name__ == '__main__':
    unittest.main()

