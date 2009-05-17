# Copyright 2009 Canonical Ltd.  All rights reserved.
"""
Run the doctests and pagetests.
"""

import os
from lp.services.testing import build_test_suite

here = os.path.dirname(os.path.realpath(__file__))

def test_suite():
    return build_test_suite(here)
