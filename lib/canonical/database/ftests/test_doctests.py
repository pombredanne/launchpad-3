# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite
from canonical.testing import DatabaseLayer, LaunchpadLayer


def test_suite():
    return unittest.TestSuite([
            LayeredDocFileSuite(
                'test_disconnects.txt',
                'test_multitablecopy.txt',
                'test_reconnector.txt',
                'test_reconnect_already_closed.txt',
                layer=DatabaseLayer, stdout_logging=False),
            LayeredDocFileSuite(
                'test_zopelesstransactionmanager.txt',
                'test_zopeless_reconnect.txt',
                layer=LaunchpadLayer, stdout_logging=False),
            ])

