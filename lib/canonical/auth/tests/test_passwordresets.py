import unittest
from zope.testing.doctest import DocFileSuite, DocTestSuite

def test_suite():
    suite = unittest.TestSuite((
        DocFileSuite(
        "password_resets.txt", globs = {}),))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest = "test_suite")
