from canonical.launchpad.windmill.testing import lpuser

from windmill.authoring import WindmillTestClient

def test_mark_duplicate_form_overlay():
    """Test the mark duplicate action on bug pages.

    This test ensures that with Javascript enabled, the mark duplicate link
    on a bug page uses the formoverlay to update the duplicateof field via
    the api.
    """
    client = WindmillTestClient("Bug mark duplicate test")
    lpuser.SAMPLE_PERSON.ensure_login(client)

    # Open a bug page and wait for it to finish loading
    client.open(url=u'http://bugs.launchpad.dev:8085/bugs/15')
    client.waits.forPageLoad(timeout=u'20000')
    client.waits.forElement(classname=u'menu-link-mark-dupe', timeout=u'8000')

    # Initially the form overlay is hidden
    client.asserts.assertNode(classname=u'yui-lazr-formoverlay-hidden')

    # Clicking on the mark duplicate link brings up the formoverlay.
    # Entering 1 as the duplicate ID changes the duplicate text.
    client.click(classname=u'menu-link-mark-dupe')
    client.asserts.assertNotNode(classname=u'yui-lazr-formoverlay-hidden')

    # Entering the bug id '1' and changing hides the formoverlay
    # and updates the mark as duplicate:
    client.type(text=u'1', id=u'field.duplicateof')
    client.click(name=u'field.actions.change')
    client.asserts.assertNode(classname=u'yui-lazr-formoverlay-hidden')
    client.waits.sleep(milliseconds=u'1000')
    client.asserts.assertText(
        xpath=u"//span[@id='mark-duplicate-text']/a[1]",
        validator=u'bug #1')

    # The duplicate can be cleared:
    client.click(classname=u'menu-link-mark-dupe')
    client.type(text=u'', id=u'field.duplicateof')
    client.click(name=u'field.actions.change')
    client.waits.sleep(milliseconds=u'1000')
    client.asserts.assertText(
        xpath=u"//span[@id='mark-duplicate-text']/a[1]",
        validator=u'Mark as duplicate')

    # Entering a false bug number results in input validation errors
    client.click(classname=u'menu-link-mark-dupe')
    client.type(text=u'123', id=u'field.duplicateof')
    client.click(name=u'field.actions.change')
    client.waits.sleep(milliseconds=u'1000')
    client.asserts.assertNode(
        xpath=u"//form[@id='lazr-formoverlay-form']/div[2]/ul/li")

    # Clicking change again brings back the error dialog again
    # (regression test for bug 347258)
    client.click(name=u'field.actions.change')
    client.waits.sleep(milliseconds=u'1000')
    client.asserts.assertNode(
        xpath=u"//form[@id='lazr-formoverlay-form']/div[2]/ul/li")

    # But entering a correct bug and submitting gets us back to a normal state
    client.type(text=u'1', id=u'field.duplicateof')
    client.click(name=u'field.actions.change')
    client.waits.sleep(milliseconds=u'1000')
    client.asserts.assertText(
        xpath=u"//span[@id='mark-duplicate-text']/a[1]",
        validator=u'bug #1')

    # Finally, clicking on the link to the bug takes you to the master.
    client.click(link=u'bug #1')
    client.waits.forPageLoad(timeout=u'20000')
    client.asserts.assertText(
        xpath=u"//h1[@id='bug-title']/span[1]",
        validator=u'Firefox does not support SVG')

