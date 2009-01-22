from windmill.authoring import WindmillTestClient

from canonical.launchpad.windmill.testing import lpuser

def test_title_inline_edit():
    """Tests that the bug title inline edit works."""
    client = WindmillTestClient(__name__)

    lpuser.SAMPLE_PERSON.ensure_login(client)

    client.open(url='http://launchpad.dev:8085/firefox')
    client.waits.forPageLoad(timeout=u'20000')
    client.waits.forElement(
        xpath=u"//h1[@id='product-title']/a/img", timeout=u'8000')
    client.asserts.assertText(
        xpath=u"//h1[@id='product-title']/span[1]",
        validator=u'Mozilla Firefox')
    client.click(xpath=u"//h1[@id='product-title']/a/img")
    client.waits.forElement(
        xpath=u"//h1[@id='product-title']/a/img", timeout=u'8000')
    client.waits.forElement(
        timeout=u'8000', xpath=u"//h1[@id='product-title']//input")
    client.type(
        xpath=u"//h1[@id='product-title']//input",
        text=u'The awesome Mozilla Firefox')
    client.click(xpath=u"//h1[@id='product-title']//button[1]")
    client.asserts.assertNode(xpath=u"//h1[@id='product-title']/span[1]")
    client.asserts.assertText(
        xpath=u"//h1[@id='product-title']/span[1]",
        validator=u'The awesome Mozilla Firefox')

    # And make sure it's actually saved on the server.
    client.open(url='http://launchpad.dev:8085/firefox')
    client.waits.forPageLoad(timeout=u'20000')
    client.asserts.assertNode(xpath=u"//h1[@id='product-title']/span[1]")
    client.asserts.assertText(
        xpath=u"//h1[@id='product-title']/span[1]",
        validator=u'The awesome Mozilla Firefox')
