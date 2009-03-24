# Copyright 2009 Canonical Ltd.  All rights reserved.

from canonical.launchpad.windmill.testing.widgets import (
    FormPickerWidgetTest)


test_new_product_part_of_project = FormPickerWidgetTest(
    name='test_new_product_part_of_project',
    url='http://launchpad.dev:8085/projects/+new',
    short_field_name='project',
    search_text='mirrors',
    result_index=1,
    new_value='launchpad-mirrors')
