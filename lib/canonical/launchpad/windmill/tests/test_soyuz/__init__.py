from canonical.launchpad.windmill.testing import lpuser
from canonical.launchpad.windmill.testing import widgets


test_ppa_displayname_inline_edit = widgets.InlineEditorWidgetTest(
    url='http://bugs.launchpad.dev:8085/~cprov/+archive/ppa',
    widget_id='displayname',
    expected_value='PPA for Celso Providelo',
    new_value="Celso's default PPA",
    name='test_ppa_displayname_inline_edit',
    user=lpuser.FOO_BAR,
    suite=__name__)
