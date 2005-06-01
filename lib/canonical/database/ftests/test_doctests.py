import unittest
from zope.testing.doctest import DocFileSuite, DocTestSuite
from zope.testing.doctest import REPORT_NDIFF, NORMALIZE_WHITESPACE, ELLIPSIS

def test_suite():
    suite = unittest.TestSuite([
        DocFileSuite('test_disconnects.txt',
                    optionflags=REPORT_NDIFF|NORMALIZE_WHITESPACE),
        DocFileSuite('test_reconnector.txt',
                     optionflags=REPORT_NDIFF|NORMALIZE_WHITESPACE),
        DocFileSuite('test_reconnect_already_closed.txt',
                     optionflags=REPORT_NDIFF|NORMALIZE_WHITESPACE),
        DocFileSuite('test_zopelesstransactionmanager.txt',
                     optionflags=REPORT_NDIFF|NORMALIZE_WHITESPACE),
        DocFileSuite('test_zopeless_reconnect.txt',
                     optionflags=ELLIPSIS|REPORT_NDIFF|NORMALIZE_WHITESPACE),
    ])
    return suite

