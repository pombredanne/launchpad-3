# arch-tag: a84c97ba-4b1f-417c-91ed-8b0685642d66

import os, unittest

from canonical.functional import FunctionalDocFileSuite

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(FunctionalDocFileSuite('page-tests/rosetta-homepage.txt'))
    suite.addTest(FunctionalDocFileSuite('page-tests/malone-homepage.txt'))
    suite.addTest(FunctionalDocFileSuite('page-tests/malone-bug-list.txt'))
    suite.addTest(FunctionalDocFileSuite('page-tests/malone-bug-index.txt'))
    return suite

if __name__ == '__main__':
    r = unittest.TextTestRunner().run(test_suite())
