# Copyright (C) 2004 Canonical Ltd.
# Authors : Robert Collins <robert.collins@canonical.com>
# Tests that various database modules can be imported.

import unittest
import sys

class TestImports(unittest.TestCase):
    def testSourceSource(self):
        '''test importing canonical.launchpad.database.sourcesource'''
        import canonical.launchpad.database.sourcesource

def test_suite():
    return unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    

