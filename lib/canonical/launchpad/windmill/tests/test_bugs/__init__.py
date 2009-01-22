from windmill.authoring import WindmillTestClient

from canonical.launchpad.windmill.testing import lpuser


def test_title_inline_edit():
    """Tests that the bug title inline edit works."""
    client = WindmillTestClient(__name__)

    lpuser.NO_PRIV.ensure_login(client)

    client.open(url='http://bugs.launchpad.dev:8085/redfish/+bug/15')
    client.waits.forPageLoad(timeout=u'20000')
    client.waits.forElement(
        xpath=u"//h1[@id='bug-title']/a/img", timeout=u'8000')
    client.asserts.assertText(
        xpath=u"//h1[@id='bug-title']/span[1]",
        validator=u'Nonsensical bugs are useless')
    client.click(xpath=u"//h1[@id='bug-title']/a/img")
    client.waits.forElement(
        xpath=u"//h1[@id='bug-title']/a/img", timeout=u'8000')
    client.waits.forElement(
        timeout=u'8000', xpath=u"//h1[@id='bug-title']//input")
    client.type(
        xpath=u"//h1[@id='bug-title']//input",
        text=u'Nonsensical bugs are often useless')
    client.click(xpath=u"//h1[@id='bug-title']//button[1]")
    client.asserts.assertNode(xpath=u"//h1[@id='bug-title']/span[1]")
    client.asserts.assertText(
        xpath=u"//h1[@id='bug-title']/span[1]",
        validator=u'Nonsensical bugs are often useless')

    # And make sure it's actually saved on the server.
    client.open(url='http://bugs.launchpad.dev:8085/redfish/+bug/15')
    client.waits.forPageLoad(timeout=u'20000')
    client.asserts.assertNode(xpath=u"//h1[@id='bug-title']/span[1]")
    client.asserts.assertText(
        xpath=u"//h1[@id='bug-title']/span[1]",
        validator=u'Nonsensical bugs are often useless')
