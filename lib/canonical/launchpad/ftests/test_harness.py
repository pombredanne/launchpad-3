import unittest
from zope.app import zapi
from harness import LaunchpadTestCase, LaunchpadFunctionalTestCase
from zope.app.mail.interfaces import IMailer


class TestLaunchpadTestCase(LaunchpadTestCase):
    def test_sampledata(self):
        con = self.connect()
        cur = con.cursor()
        cur.execute("""
            select count(*) from person 
            where displayname='Mark Shuttleworth'
            """)
        r = cur.fetchone()
        self.failUnlessEqual(r[0], 1, 'sample data not loaded')
        cur.close()
        con.close()

class TestLaunchpadFunctionalTestCase(LaunchpadFunctionalTestCase):
    def test_sampledata(self):
        con = self.connect()
        cur = con.cursor()
        cur.execute("""
            select count(*) from person 
            where displayname='Mark Shuttleworth'
            """)
        r = cur.fetchone()
        self.failUnlessEqual(r[0], 1, 'sample data not loaded')
        cur.close()
        con.close()

    def test_placeless(self):
        # Do something that requires functional machinery loaded
        zapi.getUtility(IMailer, 'smtp')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestLaunchpadTestCase))
    suite.addTest(unittest.makeSuite(TestLaunchpadFunctionalTestCase))
    return suite

if __name__ == '__main__':
    unittest.main()

