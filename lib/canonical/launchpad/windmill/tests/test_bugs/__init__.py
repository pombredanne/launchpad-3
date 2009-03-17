from canonical.launchpad.windmill.testing import lpuser
from canonical.launchpad.windmill.testing import widgets

from windmill.authoring import WindmillTestClient

test_title_inline_edit = widgets.InlineEditorWidgetTest(
    url='http://bugs.launchpad.dev:8085/redfish/+bug/15',
    widget_id='bug-title',
    expected_value='Nonsensical bugs are useless',
    new_value='Nonsensical bugs are often useless',
    name='test_title_inline_edit',
    suite=__name__)

def test_bugfilters_portlet():
    """Test that the subscribers portlet on a bug page.

    Test that the contents of the bugfilter portlet on
    a distribution page loads successfully after the page loads.
    """
    client = WindmillTestClient('Bugfilter portlet test')
    client.open(url='http://bugs.launchpad.dev:8085/ubuntu')
    client.waits.forPageLoad(timeout=u'20000')
    client.waits.forElement(
        xpath=u"//div[@id='portlet-bugfilters']", timeout=u'8000')
    client.waits.forElement(
        xpath=u"//div[@id='bugfilters-portlet-spinner']", timeout="8000")
    # The bugfilter portlet is available and the
    # spinner is hidden.
    client.asserts.assertProperty(
        xpath=u"//div[@id='bugfilters-portlet-spinner']",
        validator=u"style.display|none")
    client.asserts.assertText(
        xpath=u"//div[@id='portlet-bugfilters']",
        validator=u"All bugs ever reported")
