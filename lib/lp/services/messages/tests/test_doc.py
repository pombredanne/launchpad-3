# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Run the doctests.
"""

import os

from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite,
    setUp,
    tearDown,
    )
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.services.testing import build_test_suite


here = os.path.dirname(os.path.realpath(__file__))


special = {
    'message.txt': LayeredDocFileSuite(
        '../doc/message.txt',
        setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctionalLayer),
    }


def test_suite():
    suite = build_test_suite(here, special, layer=LaunchpadFunctionalLayer)
    return suite
