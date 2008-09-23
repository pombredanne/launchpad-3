# Copyright 2004-2008 Canonical Ltd.  All rights reserved.
import unittest
from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite

def test_suite():
    return LayeredDocFileSuite('pidfile.txt', stdout_logging=False)

if __name__ == "__main__":
    DEFAULT = test_suite()
    unittest.main(defaultTest='DEFAULT')
