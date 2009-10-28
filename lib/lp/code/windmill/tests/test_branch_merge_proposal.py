# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for the main branch merge proposal page."""

__metaclass__ = type
__all__ = []

import transaction
import unittest

from windmill.authoring import WindmillTestClient

from canonical.launchpad.windmill.testing.constants import PAGE_LOAD
from canonical.launchpad.windmill.testing.lpuser import login_person
from lp.code.windmill.testing import canonical_url, CodeWindmillLayer
from lp.testing import TestCaseWithFactory


EDIT_COMMIT_LINK = u'//a[contains(@href, "+edit-commit-message")]'
# There seem to be two textareas rendered for the yui-ieditor-input for some
# reason.
EDIT_COMMENT_TEXTBOX = (
    u'//div[@id="edit-description"]//textarea[@class="yui-ieditor-input"][1]')
EDIT_COMMENT_SUBMIT = (
    u'//div[@id="edit-description"]//'
    'button[contains(@class, "yui-ieditor-submit_button")]')
COMMIT_MESSAGE_TEXT = (
    u'//div[@id="edit-description"]//div[@class="yui-editable_text-text"]')


class TestCommitMessage(TestCaseWithFactory):

    layer = CodeWindmillLayer

    def test_set_commit_message(self):
        """Test the commit message multiline editor."""
        eric = self.factory.makePerson(
            name="eric", displayname="Eric the Viking", password="test",
            email="eric@example.com")
        bmp = self.factory.makeBranchMergeProposal(registrant=eric)
        transaction.commit()

        client = WindmillTestClient("Commit message editing.")

        login_person(eric, "test", client)

        client.open(url=canonical_url(bmp))
        client.waits.forPageLoad(timeout=PAGE_LOAD)

        # Click on the element containing the branch status.
        client.click(xpath=EDIT_COMMIT_LINK)
        client.waits.forElement(xpath=EDIT_COMMENT_TEXTBOX)

        # Edit the commit message.
        message = u"This is the commit message."
        client.type(text=message, xpath=EDIT_COMMENT_TEXTBOX)
        client.click(xpath=EDIT_COMMENT_SUBMIT)

        client.waits.forElement(xpath=COMMIT_MESSAGE_TEXT)
        client.asserts.assertText(
            xpath=COMMIT_MESSAGE_TEXT, validator=message)

        # Confirm that the change was saved.
        client.open(url=canonical_url(bmp))
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        client.asserts.assertText(
            xpath=COMMIT_MESSAGE_TEXT, validator=message)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
