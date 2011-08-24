# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Run the doctests and pagetests.
"""

import logging
import os

from lp.services.mail.tests.test_doc import (
    ProcessMailLayer,
    )
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite,
    setUp,
    tearDown,
    )
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
