# arch-tag: a84c97ba-4b1f-417c-91ed-8b0685642d66

import os, unittest

#from zope.app.tests.functional import FunctionalDocFileSuite
from canonical.functional import FunctionalDocFileSuite

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(FunctionalDocFileSuite('halibut.txt'))
    suite.addTest(FunctionalDocFileSuite('mackerel.txt'))
    suite.addTest(FunctionalDocFileSuite('herring.txt'))
    return suite

if __name__ == '__main__':
    r = unittest.TextTestRunner().run(test_suite())
