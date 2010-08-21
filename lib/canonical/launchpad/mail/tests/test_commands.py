# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from doctest import DocTestSuite
import unittest


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite('canonical.launchpad.mail.commands'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
