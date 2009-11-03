# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import unittest

from windmill.authoring import WindmillTestClient

from canonical.launchpad.windmill.testing import lpuser, constants
from lp.bugs.windmill.testing import BugsWindmillLayer
from lp.testing import TestCaseWithFactory


class TestFilebugExtras(TestCaseWithFactory):

    layer = BugsWindmillLayer

    def test_filebug_extra_options(self):
        """Test the extra options area on +filebug pages.

        This test ensures that, with Javascript enabled, the extra options
        expander starts closed, and contains several fields when opened.
        """
        client = WindmillTestClient("File bug extra options test")
        lpuser.SAMPLE_PERSON.ensure_login(client)

        # Open a +filebug page and wait for it to finish loading.
        client.open(url=u'http://bugs.launchpad.dev:8085/firefox/+filebug')
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)

        # Search for a possible duplicate.
        client.type(text=u'Broken', id=u'field.title')
        client.waits.forElement(
            id=u'field.actions.search', timeout=constants.FOR_ELEMENT)
        client.click(id=u'field.actions.search')
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)

        # No duplicates were found.
        client.asserts.assertText(
            xpath=u"//div[@class='top-portlet']//p",
            validator=u'No similar bug reports were found.')

        # Check out the expander.
        _test_expander(client)


def _test_expander(client):
    # The collapsible area is present and collapsed.
    collapsible_area_xpath = (
        u"//form[@name='launchpadform']"
        u"//fieldset[contains(.//legend,'Extra options')]")
    closed_area_xpath = (
        collapsible_area_xpath +
        u"/div[@class='collapseWrapper lazr-closed']")
    opened_area_xpath = (
        collapsible_area_xpath +
        u"/div[@class='collapseWrapper lazr-opened']")
    client.asserts.assertProperty(
        xpath=collapsible_area_xpath,
        validator="className|collapsible")
    client.asserts.assertNode(xpath=closed_area_xpath)

    # The extra options are not visible.
    client.asserts.assertProperty(
        xpath=closed_area_xpath,
        validator='style.height|0px')
    # Click on the legend and it expands.
    client.click(
        xpath=collapsible_area_xpath + u"/legend/a")
    client.waits.forElement(
        xpath=opened_area_xpath, timeout=constants.FOR_ELEMENT)

    # The extra options are visible now.
    client.asserts.assertElemJS(
        xpath=opened_area_xpath,
        js='element.style.height != "0px"')

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
