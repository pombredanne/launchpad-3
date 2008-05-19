# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite
from canonical.testing import LaunchpadScriptLayer


def test_suite():
    return unittest.TestSuite([
            LayeredDocFileSuite(
                'test_multitablecopy.txt',
                'test_zopelesstransactionmanager.txt',
                layer=LaunchpadScriptLayer, stdout_logging=False),
            ])

