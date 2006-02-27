import unittest
from zope.testing.doctestunit import DocTestSuite

def test_suite():
    # TODO: Needs to talk to a stub bugzilla - network too painful
    return unittest.TestSuite()
    return DocTestSuite('canonical.malone.externalsystem')

if __name__ == '__main__':
    unittest.main(test_suite())

