# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for the bug status entry."""

__metaclass__ = type
__all__ = []

import unittest

from canonical.launchpad.windmill.testing import constants, lpuser
from lp.bugs.windmill.testing import BugsWindmillLayer
from lp.testing import WindmillTestCase

class TestBugStatusConfirmation(WindmillTestCase):

    layer = BugsWindmillLayer
    suite_name = "Bug status confirmation step test"

    def test_bug_status_confirmation(self):
        """Test the confirmation step of the bug status entry."""
        client = self.client

        # Open a bug page and wait for it to finish loading
        client.open(url=u'http://bugs.launchpad.dev:8085/bugs/4')
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        # NO_PRIV must confirm editting the bug status in this project.
        lpuser.NO_PRIV.ensure_login(client)
        client.waits.forElement(
            xpath=u"//div[@class='status-content yui-bugstatusedit-content']//img[@class='editicon']",
            timeout=constants.FOR_ELEMENT)

        # Initially, the bug status is New.
        client.asserts.assertText(
            xpath=u"//div[contains(@class, 'status-content')]//a[1]",
            validator=u"New")
        client.click(
            xpath=u"//div[contains(@class, 'status-content')]//img[@class='editicon']")
        client.waits.forElement(
            id=u'yui-pretty-overlay-modal', timeout=constants.FOR_ELEMENT)
        # We open the status editor and change the status to In Progress.
        # When a confirmation dialog is shown, we will choose to cancel.
        client.commands.execJS(code=u"windmill.confirmAnswer = false")
        client.click(
            xpath=u"//div[@id='yui-pretty-overlay-modal']"
                  u"//a[contains(@href, '#In Progress')]")
        # The status didn't change.
        client.asserts.assertText(
            xpath=u"//div[contains(@class, 'status-content')]//a[1]",
            validator=u"New")

        # We repeat the same sequence.
        client.click(
            xpath=u"//div[contains(@class, 'status-content')]//img[@class='editicon']")
        client.waits.forElement(
            id=u'yui-pretty-overlay-modal', timeout=constants.FOR_ELEMENT)
        # This time, when the confirmation dialog appears, we will confirm.
        client.commands.execJS(code=u"windmill.confirmAnswer = true")
        client.click(
            xpath=u"//div[@id='yui-pretty-overlay-modal']"
                  u"//a[contains(@href, '#In Progress')]")
        # The status changed to In Progress.
        client.asserts.assertText(
            xpath=u"//div[contains(@class, 'status-content')]//a[1]",
            validator=u"In Progress")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
