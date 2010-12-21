# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test harness for running the potmsgset-update-translations test.

Corner case tests for IPOTMsgSet.updateTranslation.
"""

__metaclass__ = type

__all__ = []

from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite,
    setUp,
    tearDown,
    )
from canonical.testing.layers import LaunchpadFunctionalLayer


def test_suite():
    return LayeredDocFileSuite(
        'potmsgset-update-translation.txt', setUp=setUp, tearDown=tearDown,
        layer=LaunchpadFunctionalLayer)
