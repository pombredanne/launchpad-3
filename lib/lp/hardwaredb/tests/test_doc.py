# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Run the doctests and pagetests.
"""

import logging
import os
import transaction

from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.testing import (
    DatabaseLayer, DatabaseFunctionalLayer, LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer)

from lp.registry.tests import mailinglists_helper
from lp.services.testing import build_test_suite


here = os.path.dirname(os.path.realpath(__file__))


def hwdbDeviceTablesSetup(test):
    setUp(test)
    LaunchpadZopelessLayer.switchDbUser('hwdb-submission-processor')


special = {
    'hwdb-device-tables.txt': LayeredDocFileSuite(
        '../doc/hwdb-device-tables.txt',
        setUp=hwdbDeviceTablesSetup,
        tearDown=tearDown,
        layer=LaunchpadZopelessLayer,
        ),
    }


def test_suite():
    return build_test_suite(here, special, layer=LaunchpadFunctionalLayer)
