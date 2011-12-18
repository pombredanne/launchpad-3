# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Run the doctests and pagetests.
"""

__metaclass__ = type

import os

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.services.testing import build_test_suite


here = os.path.dirname(os.path.realpath(__file__))


special = {
    'test_adapter.txt': LayeredDocFileSuite(
        '../doc/test_adapter.txt',
        layer=LaunchpadFunctionalLayer),
# XXX Julian 2009-05-13, bug=376171
# Temporarily disabled because of intermittent failures.
#    'test_adapter_timeout.txt': LayeredDocFileSuite(
#        '../doc/test_adapter_timeout.txt',
#        setUp=setUp,
#        tearDown=tearDown,
#        layer=LaunchpadFunctionalLayer),
    'test_adapter_permissions.txt': LayeredDocFileSuite(
        '../doc/test_adapter_permissions.txt',
        layer=LaunchpadFunctionalLayer),
    }


def test_suite():
    return build_test_suite(here, special, layer=LaunchpadFunctionalLayer)
