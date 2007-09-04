# Copyright (C) 2004 Canonical Ltd.
# Authors : Robert Collins <robert.collins@canonical.com>
# Tests that various database modules can be imported.

import unittest
import sys

def test_suite():
    return unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])


