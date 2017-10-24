# Copyright 2010-2017 Canonical Ltd.  This software is licensed under the
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


class SnappyYUIUnitTestCase(YUIUnitTestCase):

    layer = YUITestLayer
    suite_name = 'SnappyYUIUnitTests'


def test_suite():
    app_testing_path = 'lp/snappy'
    return build_yui_unittest_suite(app_testing_path, SnappyYUIUnitTestCase)
