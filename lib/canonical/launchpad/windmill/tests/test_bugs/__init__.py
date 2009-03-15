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

def test_subscribers_portlet():
    """Test that the subscribers portlet on a bug page.
    
    Test that the contents of the subscribers portlet on
    a bug page loads successfully after the page loads.
    """
    client = WindmillTestClient('Bug subscribers portlet test')
    # We open a bug page, and wait for it to load
    client.open(url='http://bugs.launchpad.dev:8085/bugs/15')
    client.waits.forPageLoad(timeout=u'20000')
    client.waits.forElement(
        xpath=u"//div[@id='portlet-subscribers']", timeout=u'8000')
    # The subscribers portlet is available and the
    # spinner is hidden.
    client.asserts.assertProperty(
        xpath=u"//div[@id='portlet-subscribers']//"
              u"div[@id='subscribers-portlet-spinner']",
        validator="style.display|none")
    # The details for ~foobar are present inside the portlet,
    # which means that the contents were loaded correctly.
    client.asserts.assertNode(
        xpath=u"//div[@id='portlet-subscribers']//a[@href='/~name16']")

