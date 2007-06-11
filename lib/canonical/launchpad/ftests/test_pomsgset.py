# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test harness for running the pomsgset-update-translation-set test.

Corner case tests for IPOMsgSet.updateTranslationSet.
"""

__metaclass__ = type

__all__ = []

import unittest

from canonical.functional import FunctionalDocFileSuite
from canonical.testing import LaunchpadFunctionalLayer
from canonical.launchpad.ftests.test_system_documentation import (
    default_optionflags, setUp, tearDown)


def test_suite():
    return FunctionalDocFileSuite(
        'pomsgset-update-translation-set.txt', setUp=setUp, tearDown=tearDown,
        optionflags=default_optionflags, package=__name__,
        layer=LaunchpadFunctionalLayer)
