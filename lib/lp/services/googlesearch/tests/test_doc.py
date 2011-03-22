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
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    GoogleLaunchpadFunctionalLayer,
    )
from lp.services.testing import build_test_suite


here = os.path.dirname(os.path.realpath(__file__))


special = {
    'google-searchservice.txt': LayeredDocFileSuite(
        '../doc/google-searchservice.txt',
        setUp=setUp, tearDown=tearDown,
        layer=GoogleLaunchpadFunctionalLayer,),
    }


def test_suite():
    suite = build_test_suite(here, special, layer=DatabaseFunctionalLayer)
    return suite
