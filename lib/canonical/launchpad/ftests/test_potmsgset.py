# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test harness for running the potmsgset-update-translations test.

Corner case tests for IPOTMsgSet.updateTranslation.
"""

__metaclass__ = type

__all__ = []

from canonical.testing import LaunchpadFunctionalLayer
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)


def test_suite():
    return LayeredDocFileSuite(
        'potmsgset-update-translation.txt', setUp=setUp, tearDown=tearDown,
        layer=LaunchpadFunctionalLayer)
