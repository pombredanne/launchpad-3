# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Run YUI.test tests."""

__metaclass__ = type
__all__ = []

from canonical.testing.layers import BaseYUITestLayer
from lp.testing import (
    build_yui_unittest_suite,
    YUIUnitTestCase,
    )


class RegistryYUITestLayer(BaseYUITestLayer):
    """Layer for Code YUI tests."""


class RegistryYUIUnitTestCase(YUIUnitTestCase):

    layer = RegistryYUITestLayer
    suite_name = 'RegistryYUIUnitTests'


def test_suite():
    app_testing_path = 'lp/registry/javascript/tests'
    return build_yui_unittest_suite(app_testing_path, RegistryYUIUnitTestCase)
