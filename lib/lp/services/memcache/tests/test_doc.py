# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Run doctests."""

__metaclass__ = type

import os.path
import unittest

from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.services.testing import build_test_suite
from lp.testing import TestCase

here = os.path.dirname(os.path.realpath(__file__))

def test_suite():
    return build_test_suite(here, {}, layer=LaunchpadFunctionalLayer)
