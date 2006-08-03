import unittest
from zope.testing.doctest import REPORT_NDIFF, NORMALIZE_WHITESPACE, ELLIPSIS

from canonical.functional import FunctionalDocFileSuite
from canonical.testing import LibrarianLayer

def test_suite():
    suite = unittest.TestSuite([
        FunctionalDocFileSuite('archivepublisher/ftests/test_bug_54039.txt',
                               optionflags=REPORT_NDIFF|NORMALIZE_WHITESPACE,
                               layer=LibrarianLayer),
    ])
    return suite

