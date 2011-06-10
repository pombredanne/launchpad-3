# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import unittest

from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite,
    setUp,
    tearDown,
    )
from canonical.testing.layers import LaunchpadFunctionalLayer


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(LayeredDocFileSuite(
        'bug-portlet-subscribers-content.txt', setUp=setUp, tearDown=tearDown,
        layer=LaunchpadFunctionalLayer))
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())
