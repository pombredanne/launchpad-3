from canonical.launchpad.windmill.testing import lpuser

from windmill.authoring import WindmillTestClient


def test_filebug_extra_options():
    """Test the extra options area on +filebug pages.

    This test ensures that, with Javascript enabled, the extra options
    expander starts closed, and contains several fields when opened.
    """
    client = WindmillTestClient("File bug extra options test")
    lpuser.SAMPLE_PERSON.ensure_login(client)

    # Open a +filebug page and wait for it to finish loading.
    client.open(url=u'http://bugs.launchpad.dev:8085/firefox/+filebug')
    client.waits.forPageLoad(timeout=u'20000')

    # Search for a possible duplicate.
    client.type(text=u'Broken', id=u'field.title')
    client.click(id=u'field.actions.search')
    client.waits.forPageLoad(timeout=u'20000')

    # No duplicates were found.
    client.asserts.assertText(
        xpath=u"//form[@name='launchpadform']//p",
        validator=u'No similar bug reports were found.')

    # Check out the expander.
    _test_expander(client)


def test_advanced_filebug_extra_options():
    """Test the extra options area on +filebug-advanced pages.

    See `test_filebug_extra_options`.
    """
    client = WindmillTestClient("File bug extra options test")
    lpuser.SAMPLE_PERSON.ensure_login(client)

    # Open a +filebug-advanced page and wait for it to finish loading.
    client.open(
        url=u'http://bugs.launchpad.dev:8085/firefox/+filebug-advanced')
    client.waits.forPageLoad(timeout=u'20000')

    # Check out the expander.
    _test_expander(client)


def _test_expander(client):
    # The collapsible area is present and collapsed.
    collapsible_area_xpath = (
        u"//form[@name='launchpadform']"
        u"//fieldset[contains(.//legend,'Extra options')]")
    client.asserts.assertProperty(
        xpath=collapsible_area_xpath,
        validator="className|collapsible")
    client.asserts.assertNode(
        xpath=collapsible_area_xpath + u"/div[@class='collapsed']")

    # The extra options are not visible.
    extra_options_ids = (
        u"field.filecontent",
        u"field.patch",
        u"field.attachment_description",
        )
    for extra_option_id in extra_options_ids:
        client.asserts.assertElemJS(
            id=extra_option_id, js=u"element.clientWidth == 0")

    # Click on the legend and it expands.
    client.click(
        xpath=collapsible_area_xpath + u"/legend/a")
    client.waits.forElement(
        xpath=collapsible_area_xpath + u"/div[@class='expanded']")

    # The extra options are visible now.
    for extra_option_id in extra_options_ids:
        client.asserts.assertElemJS(
            id=extra_option_id, js=u"element.clientWidth > 0")
