# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite
from canonical.testing.layers import LaunchpadScriptLayer


def test_suite():
    return unittest.TestSuite([
            LayeredDocFileSuite(
                'test_multitablecopy.txt',
                'test_sqlbaseconnect.txt',
                layer=LaunchpadScriptLayer, stdout_logging=False),
            ])
