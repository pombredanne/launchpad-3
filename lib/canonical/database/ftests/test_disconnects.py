import unittest
from zope.testing.doctest import DocFileSuite, DocTestSuite
from zope.testing.doctest import REPORT_NDIFF, NORMALIZE_WHITESPACE

def test_suite():
    # XXX: Disabled - failing through PQM. StuartBishop 20050208
    suite = unittest.TestSuite([
        DocFileSuite('test_disconnects.txt',
                     optionflags=REPORT_NDIFF|NORMALIZE_WHITESPACE),
        DocFileSuite('test_reconnector.txt',
                     optionflags=REPORT_NDIFF|NORMALIZE_WHITESPACE),
        DocFileSuite('test_reconnect_already_closed.txt',
                     optionflags=REPORT_NDIFF|NORMALIZE_WHITESPACE),
    ])
    return suite

