# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Run YUI.test tests."""

__metaclass__ = type
__all__ = []

from canonical.testing.layers import BaseYUITestLayer
from lp.testing import (
    build_yui_unittest_suite,
    YUIUnitTestCase,
    )


class TranslationsYUITestLayer(BaseYUITestLayer):
    """Layer for Translations YUI tests."""


class TranslationsYUIUnitTestCase(YUIUnitTestCase):

    layer = TranslationsYUITestLayer
    suite_name = 'TranslationsYUIUnitTests'


def test_suite():
    app_testing_path = 'lp/translations/javascript/tests'
    return build_yui_unittest_suite(
            app_testing_path,
            TranslationsYUIUnitTestCase)
