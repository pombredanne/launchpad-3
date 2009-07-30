# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from canonical.launchpad.windmill.testing import lpuser

from windmill.authoring import WindmillTestClient


def test_me_too():
    """Test the "this bug affects me too" options on bug pages.

    This test ensures that, with Javascript enabled, the "me too"
    status can be edited in-page.
    """
    client = WindmillTestClient('Bug "me too" test')
    lpuser.SAMPLE_PERSON.ensure_login(client)

    # Open bug 11 and wait for it to finish loading.
    client.open(url=u'http://bugs.launchpad.dev:8085/jokosher/+bug/11/+index')
    client.waits.forPageLoad(timeout=u'20000')

    # Wait for setup_me_too to sort out the "me too" elements.
    client.waits.forElement(
        xpath=(u"//span[@id='affectsmetoo' and "
               u"@class='yui-metoocs-content']"))

    # Currently this bug does not affect the logged-in user.
    client.asserts.assertText(
        xpath=u"//span[@id='affectsmetoo']/span[@class='value']",
        validator=u"This bug doesn't affect me")

    # There is an edit icon next to the text which can be clicked to
    # edit the "me too" status. However, we won't click it with
    # Windmill because the widget actually responds to mouse-down, and
    # Windmill seems to do something funny instead.
    client.mouseDown(
        xpath=u"//span[@id='affectsmetoo']//img[@class='editicon']")
    client.mouseUp(
        xpath=u"//span[@id='affectsmetoo']//img[@class='editicon']")

    # Wait for the modal dialog to appear.
    client.waits.forElement(id=u'yui-pretty-overlay-modal')

    # There's a close button if we change our mind.
    client.click(
        xpath=(u"//div[@id='yui-pretty-overlay-modal']//"
               u"a[@class='close-button']"))

    # Wait for the modal dialog to disappear. Unfortunately the test
    # below doesn't work, nor does testing clientWidth, or anything I
    # could think of, so it's commented out for now because chasing
    # this is not a good use of time.

    # client.asserts.assertElemJS(
    #     id=u'yui-pretty-overlay-modal',
    #     js=(u'getComputedStyle(element, '
    #         u'"visibility").visibility == "hidden"'))

    # However, we want to mark this bug as affecting the logged-in
    # user. We can also click on the content box of the "me too"
    # widget; we are not forced to use the edit icon.
    client.click(xpath=u"//span[@id='affectsmetoo']")
    client.waits.forElement(id=u'yui-pretty-overlay-modal')

    # Do more here...
