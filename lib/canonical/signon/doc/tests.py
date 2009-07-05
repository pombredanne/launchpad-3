# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

import os
import logging
import unittest

from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.testing import DatabaseFunctionalLayer


here = os.path.dirname(os.path.realpath(__file__))


def test_suite():
    filenames = sorted(filename for filename in os.listdir(here)
                       if filename.lower().endswith('.txt'))
    suite = unittest.TestSuite()
    for filename in filenames:
        if filename == 'openid-fetcher.txt':
            test = LayeredDocFileSuite(
                filename, stdout_logging=False,
                layer=DatabaseFunctionalLayer)
        else:
            test = LayeredDocFileSuite(
                filename, setUp=setUp, tearDown=tearDown,
                layer=DatabaseFunctionalLayer,
                stdout_logging_level=logging.WARNING)
        suite.addTest(test)

    return suite
