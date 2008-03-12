# Copyright 2004 Canonical Ltd.  All rights reserved.

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite


def test_suite():
    return LayeredDocFileSuite('chunkydiff.txt', stdout_logging=False)

