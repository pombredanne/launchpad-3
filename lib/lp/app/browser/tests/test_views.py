# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Run the view tests.
"""

import logging
import os

from lp.services.features.testing import FeatureFixture
from lp.services.testing import build_test_suite
from lp.testing.layers import (
    GoogleLaunchpadFunctionalLayer,
    )
from lp.testing.systemdocs import (
    LayeredDocFileSuite,
    setUp,
    tearDown,
    )


here = os.path.dirname(os.path.realpath(__file__))

# The default layer of view tests is the DatabaseFunctionalLayer. Tests
# that require something special like the librarian or mailman must run
# on a layer that sets those services up.
special = {
    'launchpad-search-pages-google.txt': LayeredDocFileSuite(
        '../doc/launchpad-search-pages-google.txt',
        setUp=setUp, tearDown=tearDown,
        layer=GoogleLaunchpadFunctionalLayer,
        stdout_logging_level=logging.WARNING),
    }


def test_suite():
    return build_test_suite(here, special)
