import unittest
from zope.testing.doctest import DocFileSuite

def test_suite():
    suite = unittest.TestSuite((DocFileSuite("soyuz_views.txt"),))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest = "test_suite")
