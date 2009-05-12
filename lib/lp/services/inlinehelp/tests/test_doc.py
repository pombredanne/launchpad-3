# Copyright 2009 Canonical Ltd.  All rights reserved.
"""
Run the doctests.
"""

import os

from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite)

def test_suite():
    return LayeredDocFileSuite('../README.txt')
