import unittest
from zope.testing.doctestunit import DocTestSuite

def test_import_works():
    '''
    There is no test harness or sample data for this yet, but
    at the very least we can ensure that it imports.

    >>> import canonical.malone.checkwatches

    '''

def test_suite():
    suite = DocTestSuite()
    #suite.addTest(DocTestSuite('canonical.malone.checkwatches'))
    return suite

if __name__ == '__main__':
    unittest.main(test_suite())

