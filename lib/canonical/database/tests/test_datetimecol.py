
import unittest
from zope.testing import doctest
import canonical.database.datetimecol

def test_suite():
    return doctest.DocTestSuite(canonical.database.datetimecol)

if __name__ == '__main__':
    unittest.main()
