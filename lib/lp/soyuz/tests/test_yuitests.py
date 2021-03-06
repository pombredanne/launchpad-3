# Copyright 2010-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Run YUI.test tests."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = []

from lp.testing import (
    build_yui_unittest_suite,
    YUIUnitTestCase,
    )
from lp.testing.layers import YUITestLayer


class SoyuzYUIUnitTestCase(YUIUnitTestCase):

    layer = YUITestLayer
    suite_name = 'SoyuzYUIUnitTests'


def test_suite():
    app_testing_path = 'lp/soyuz'
    return build_yui_unittest_suite(app_testing_path, SoyuzYUIUnitTestCase)
