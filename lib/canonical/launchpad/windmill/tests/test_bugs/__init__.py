from canonical.launchpad.windmill.testing import lpuser
from canonical.launchpad.windmill.testing import widgets

test_title_inline_edit = widgets.InlineEditorWidgetTest(
    url='http://bugs.launchpad.dev:8085/redfish/+bug/15',
    widget_id='bug-title',
    expected_value='Nonsensical bugs are useless',
    new_value='Nonsensical bugs are often useless',
    name='test_title_inline_edit',
    suite=__name__)
