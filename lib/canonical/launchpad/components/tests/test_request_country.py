# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type

from doctest import DocTestSuite
import unittest


def test_suite():
    import canonical.launchpad.components.request_country
    return DocTestSuite(canonical.launchpad.components.request_country)

if __name__ == '__main__':
    DEFAULT = test_suite()
    unittest.main(defaultTest='DEFAULT')

