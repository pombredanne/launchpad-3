# Copyright 2009 Canonical Ltd.  All rights reserved.
"""
Run the doctests and pagetests.
"""

import logging
import os
import unittest

from canonical.launchpad.testing.pages import PageTestSuite
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.launchpad.ftests.test_system_documentation import(
    ProcessMailLayer)
from canonical.testing import DatabaseFunctionalLayer

from lp.services.testing import build_test_suite


here = os.path.dirname(os.path.realpath(__file__))


special = {
    'spec-mail-exploder.txt': LayeredDocFileSuite(
        "../doc/spec-mail-exploder.txt",
        setUp=setUp, tearDown=tearDown,
        layer=ProcessMailLayer,
        stdout_logging=True,
        stdout_logging_level=logging.WARNING),
    }


def test_suite():
    return build_test_suite(here, special)
