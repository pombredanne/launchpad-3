# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test GEOIP documentation."""

__metaclass__ = type

import os
from doctest import DocTestSuite

from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.services.testing import build_test_suite


here = os.path.dirname(os.path.realpath(__file__))


def test_suite():
    import lp.services.geoip.helpers
    inline_doctest = DocTestSuite(lp.services.geoip.helpers)
    suite = build_test_suite(here, {}, layer=LaunchpadFunctionalLayer)
    suite.addTest(inline_doctest)
    return suite
