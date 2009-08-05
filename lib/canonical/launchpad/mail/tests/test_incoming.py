# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import unittest

from zope.testing.doctest import DocTestSuite


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite('canonical.launchpad.mail.incoming'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
