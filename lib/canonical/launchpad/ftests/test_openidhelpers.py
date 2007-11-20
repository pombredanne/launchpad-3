# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Tests for OpenID test helpers."""

__metaclass__ = type

import unittest

from canonical.functional import FunctionalDocFileSuite
from canonical.testing import LaunchpadFunctionalLayer


def test_suite():
    return FunctionalDocFileSuite(
        'openid-fetcher.txt',
        layer=LaunchpadFunctionalLayer, stdout_logging=False)
