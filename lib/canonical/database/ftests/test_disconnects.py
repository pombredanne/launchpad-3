import unittest
from zope.testing.doctest import DocFileSuite, DocTestSuite
from zope.testing.doctest import REPORT_NDIFF, NORMALIZE_WHITESPACE

def test_suite():
    # XXX: Disabled because chinstrap doesn't have identd, so the tests fail there
    return unittest.TestSuite()

    suite = unittest.TestSuite([
        DocFileSuite('test_disconnects.txt',
                     optionflags=REPORT_NDIFF|NORMALIZE_WHITESPACE),
        DocFileSuite('test_reconnector.txt',
                     optionflags=REPORT_NDIFF|NORMALIZE_WHITESPACE),
    ])
    return suite

