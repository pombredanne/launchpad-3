# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Run the doctests and pagetests.
"""

import os

from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite,
    setUp,
    tearDown)
from canonical.testing import (
    DatabaseFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.services.testing import build_test_suite


here = os.path.dirname(os.path.realpath(__file__))


special = {
    'close-account.txt': LayeredDocFileSuite(
    '../doc/close-account.txt', setUp=setUp, tearDown=tearDown,
    layer=LaunchpadZopelessLayer),
    }


def test_suite():
    suite = build_test_suite(here, special, layer=DatabaseFunctionalLayer)
    return suite
