# Copyright 2005 Canonical Ltd.  All rights reserved.

import unittest

from zope.testing.doctest import DocTestSuite

from canonical.launchpad import datetimeutils


if __name__ == '__main__':
    unittest.TextTestRunner().run(DocTestSuite(datetimeutils))

