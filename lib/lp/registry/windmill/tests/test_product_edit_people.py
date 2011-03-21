# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test picker on +edit-people page."""

__metaclass__ = type
__all__ = []

import unittest

from lp.registry.windmill.testing import RegistryWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill.widgets import FormPickerWidgetTest


class TestProductEditPeople(WindmillTestCase):
    """Test picker +edit-people page."""

    layer = RegistryWindmillLayer

    def test_product_edit_people_driver(self):
        test = FormPickerWidgetTest(
            name='test_product_edit_people_driver',
            url='%s/firefox/+edit-people' % RegistryWindmillLayer.base_url,
            short_field_name='driver',
            search_text='Perell\xc3\xb3',
            result_index=1,
            new_value='carlos')
        test()

    def test_product_edit_people_owner(self):
        test = FormPickerWidgetTest(
            name='test_product_edit_people_owner',
            url='%s/firefox/+edit-people' % RegistryWindmillLayer.base_url,
            short_field_name='owner',
            search_text='guadamen',
            result_index=1,
            new_value='guadamen')
        test()


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
