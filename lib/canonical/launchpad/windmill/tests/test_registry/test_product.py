from canonical.launchpad.windmill.testing import lpuser
from canonical.launchpad.windmill.testing import widgets

test_title_inline_edit = widgets.InlineEditorWidgetTest(
    url='http://launchpad.dev:8085/firefox',
    widget_id='product-title',
    expected_value='Mozilla Firefox',
    new_value='The awesome Mozilla Firefox',
    name='test_title_inline_edit',
    suite=__name__,
    user=lpuser.SAMPLE_PERSON)
