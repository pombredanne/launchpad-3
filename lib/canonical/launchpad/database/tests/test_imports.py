# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# Authors : Robert Collins <robert.collins@canonical.com>
# Tests that various database modules can be imported.

import sys
import unittest


def test_suite():
    return unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])


