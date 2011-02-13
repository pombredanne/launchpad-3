# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import unittest

from lp.bugs.windmill.testing import BugsWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill import (
    constants,
    lpuser,
    )


FORM_OVERLAY = u'//div[@id="duplicate-overlay-bug-4"]/div'
FORM_OVERLAY_CANCEL = (
    u'//div[@id="duplicate-overlay-bug-4"]'
    '//button[@name="field.actions.cancel"]')
FORM_OVERLAY_SUBMIT = (
    u'//div[@id="duplicate-overlay-bug-4"]'
    '//button[@name="field.actions.this_is_my_bug"]')

# JavaScript expressions for testing.
FORM_NOT_VISIBLE = (
    u'element.className.search("yui3-lazr-formoverlay-hidden") != -1')
FORM_VISIBLE = (
    u'element.className.search("yui3-lazr-formoverlay-hidden") == -1')

BUG_INFO_HIDDEN = 'style.height|0px'
BUG_INFO_SHOWN_JS = 'element.style.height != "0px"'


class TestDupeFinder(WindmillTestCase):

    layer = BugsWindmillLayer
    suite_name = "Duplicate bug finder test"

    def test_duplicate_finder(self):
        """Test the +filebug duplicate finder.

        The duplicate finder should show a simple view of possible
        duplicates for a bug, with an expander that allows the user to view
        more information if they wish.
        """
        client = self.client
        lpuser.SAMPLE_PERSON.ensure_login(client)

        # Go to the +filebug page for Firefox
        client.open(url=u'%s/firefox/+filebug' % BugsWindmillLayer.base_url)
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)

        # Ensure the "search" field has finished loading, then enter a simple
        # search and hit search.
        client.waits.forElement(
            xpath=u'//input[@id="field.search"]',
            timeout=constants.FOR_ELEMENT)
        client.type(text=u'problem', id=u'field.search')
        client.click(xpath=u'//input[@id="field.actions.search"]')

        # The details div for the duplicate bug should not be shown.
        client.waits.forElementProperty(
            id='details-for-bug-4', option=BUG_INFO_HIDDEN,
            timeout=constants.FOR_ELEMENT)

        # The expander for the duplicate should be collapsed.
        client.asserts.assertProperty(
            id='bug-details-expander-bug-4',
            validator='src|/@@/treeCollapsed')

        # Initially the form overlay is hidden
        client.asserts.assertElemJS(xpath=FORM_OVERLAY, js=FORM_NOT_VISIBLE)

        # Clicking on the expander will expand it and show the details div.
        client.click(id='bug-details-expander-bug-4')
        client.waits.sleep(milliseconds=constants.SLEEP)
        client.asserts.assertProperty(
            id='bug-details-expander-bug-4', validator='src|/@@/treeExpanded')
        client.asserts.assertElemJS(
            id='details-for-bug-4', js=BUG_INFO_SHOWN_JS)

        # Clicking the expander again will hide the details div and collapse
        # the expander.
        client.click(id='bug-details-expander-bug-4')
        client.waits.sleep(milliseconds=constants.SLEEP)
        client.asserts.assertProperty(
            id='bug-details-expander-bug-4',
            validator='src|/@@/treeCollapsed')
        client.asserts.assertProperty(
            id='details-for-bug-4', validator=BUG_INFO_HIDDEN)

        # Clicking it yet again will reopen it.
        client.click(id='bug-details-expander-bug-4')
        client.waits.sleep(milliseconds=constants.SLEEP)
        client.asserts.assertProperty(
            id='bug-details-expander-bug-4', validator='src|/@@/treeExpanded')
        client.asserts.assertElemJS(
            id='details-for-bug-4', js=BUG_INFO_SHOWN_JS)

        # Clicking on the "Yes, this is my bug button" will show a form
        # overlay, which will offer the user the option to subscribe to the
        # bug.
        client.click(id="this-is-my-bug-4")
        client.waits.sleep(milliseconds=constants.SLEEP)
        client.asserts.assertElemJS(xpath=FORM_OVERLAY, js=FORM_VISIBLE)

        # Clicking the cancel button will make the overlay go away again.
        client.click(xpath=FORM_OVERLAY_CANCEL)
        client.waits.sleep(milliseconds=constants.SLEEP)
        client.asserts.assertElemJS(xpath=FORM_OVERLAY, js=FORM_NOT_VISIBLE)

        # Validation errors are displayed on the current page.
        client.click(id="bug-not-already-reported")
        client.asserts.assertProperty(
            id="filebug-form-container", validator="style.display|block",
            timeout=constants.FOR_ELEMENT)
        client.click(id="field.actions.submit_bug")
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        client.asserts.assertText(
            xpath=u'//div[@class="message"]',
            validator="Provide details about the issue.")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
