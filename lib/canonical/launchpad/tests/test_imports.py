# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite

def test_suite():
    return LayeredDocFileSuite('test_imports.txt')

