# Copyright 2005 Canonical Ltd.  All rights reserved.

import unittest

from zope.testing.doctest import DocTestSuite


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite('canonical.launchpad.mail.commands'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
