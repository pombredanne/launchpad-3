"""
Unit tests for schoolbell
"""

import unittest
from zope.testing import doctest


def doctest_interfaces():
    """Look for syntax errors in interfaces.py

        >>> import schoolbell.interfaces

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite())
    suite.addTest(doctest.DocTestSuite('schoolbell.mixins'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
