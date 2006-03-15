import unittest
import supermirror.tests.bzr_5_6
import supermirror.tests.genericbranch
import supermirror.tests.branchfactory
import supermirror.tests.testmirror
 

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(supermirror.tests.genericbranch.test_suite())
    suite.addTest(supermirror.tests.bzr_5_6.test_suite())
    suite.addTest(supermirror.tests.branchfactory.test_suite())
    suite.addTest(supermirror.tests.testmirror.test_suite())

    return suite


if __name__=='__main__': unittest.main(defaultTest='test_suite')
