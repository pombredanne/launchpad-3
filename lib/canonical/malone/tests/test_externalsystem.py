import unittest
from zope.testing.doctestunit import DocTestSuite

def test_suite():
    return DocTestSuite('canonical.malone.externalsystem')

if __name__ == '__main__':
    unittest.main(test_suite())

