"""Tests for canonical.foaf.nickname"""

# standard library imports
import doctest, unittest

from canonical.foaf import nickname


def test_suite():
    dt_suite = doctest.DocTestSuite(nickname)
    return unittest.TestSuite((dt_suite,))

