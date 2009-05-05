# Copyright 2009 Canonical Ltd.  All rights reserved.

from canonical.launchpad.windmill.testing.widgets import (
    InlinePickerWidgetButtonTest, InlinePickerWidgetSearchTest)

test_change_assignee = InlinePickerWidgetSearchTest(
    url='http://bugs.launchpad.dev:8085/bugs/1',
    suite='bugtask_assignee',
    name='test_change_assignee_button',
    activator_id='assignee-content-box-17',
    search_text='admin',
    result_index=1,
    new_value='Commercial Subscription Admins')

test_assign_me_button = InlinePickerWidgetButtonTest(
    url='http://bugs.launchpad.dev:8085/bugs/1',
    suite='bugtask_assignee',
    name='test_assign_me_button',
    activator_id='assignee-content-box-17',
    button_class='yui-picker-assign-me-button',
    new_value='Foo Bar')

test_remove_assignee_button = InlinePickerWidgetButtonTest(
    url='http://bugs.launchpad.dev:8085/bugs/1',
    suite='bugtask_assignee',
    name='test_remove_assignee_button',
    activator_id='assignee-content-box-17',
    button_class='yui-picker-remove-button',
    new_value='Nobody')
