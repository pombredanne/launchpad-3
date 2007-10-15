# Copyright 2004 Canonical Ltd.  All rights reserved.

import unittest
from zope.testing.doctest import DocTestSuite, ELLIPSIS
from canonical.launchpad.webapp import publisher

def test_suite():
    suite = DocTestSuite(publisher, optionflags=ELLIPSIS)
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
