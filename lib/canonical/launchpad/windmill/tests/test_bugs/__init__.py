from windmill.authoring import WindmillTestClient


def login(email, password):
    """Logs in the site."""
    client = WindmillTestClient(__name__)
    client.click(link=u'Log in / Register')
    client.waits.forPageLoad(timeout=u'20000')
    client.waits.forElement(timeout=u'8000', id=u'email')
    client.type(text=email, id=u'email')
    client.type(text=password, id=u'password')
    client.click(name=u'loginpage_submit_login')
    client.waits.forPageLoad(timeout=u'20000')


def logout():
    """Logs out."""
    client = WindmillTestClient(__name__)
    client.click(name="logout")
    client.waits.forPageLoad(timeout=u'20000')


def setup_module(module):
    """Run as logged in."""
    login('no-priv@canonical.com', 'test')


def teardown_module(module):
    """Logs out."""
    logout()


def test_title_inline_edit():
    """Tests that the bug title inline edit works."""
    client = WindmillTestClient(__name__)

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
