# Copyright 2009 Canonical Ltd.  All rights reserved.

from canonical.launchpad.windmill.testing.widgets import (
    InlinePickerWidgetTest)


test_change_assignee_1 = InlinePickerWidgetTest(
    url='http://bugs.launchpad.dev:8085/bugs/1',
    activator_id='assignee-content-box-2',
    search_text='admin',
    result_index=1,
    new_value='Commercial Subscription Admins')

test_change_assignee_2 = InlinePickerWidgetTest(
    url='http://bugs.launchpad.dev:8085/bugs/1',
    activator_id='assignee-content-box-17',
    search_text='admin',
    result_index=2,
    new_value='Foo Bar')
