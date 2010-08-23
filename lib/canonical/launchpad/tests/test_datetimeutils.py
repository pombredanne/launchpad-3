# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from doctest import DocTestSuite
import unittest

from canonical.launchpad import datetimeutils


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite(datetimeutils))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())

