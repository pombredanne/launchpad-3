# Copyright 2009 Canonical Ltd.  All rights reserved.

from canonical.launchpad.windmill.testing.widgets import (
    FormPickerWidgetTest)


test_product_edit_people_driver = FormPickerWidgetTest(
    name='test_product_edit_people_driver',
    url='http://launchpad.dev:8085/firefox/+edit-people',
    short_field_name='driver',
    search_text='foo',
    result_index=1,
    new_value='name16')

test_product_edit_people_owner = FormPickerWidgetTest(
    name='test_product_edit_people_owner',
    url='http://launchpad.dev:8085/firefox/+edit-people',
    short_field_name='owner',
    search_text='guadamen',
    result_index=1,
    new_value='guadamen')

