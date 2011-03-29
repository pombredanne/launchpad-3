# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for the main branch merge proposal page."""

__metaclass__ = type
__all__ = []

import transaction

from lp.code.windmill.testing import CodeWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill.constants import (
    FOR_ELEMENT,
    PAGE_LOAD,
    SLEEP,
    )


EDIT_COMMIT_LINK = u'//a[contains(@href, "+edit-commit-message")]'
# There seem to be two textareas rendered for the yui3-ieditor-input for some
# reason.
EDIT_COMMENT_TEXTBOX = (
    u'//div[@id="edit-commit_message"]//textarea[@class="yui3-ieditor-input"][1]')
EDIT_COMMENT_SUBMIT = (
    u'//div[@id="edit-commit_message"]//'
    'button[contains(@class, "yui3-ieditor-submit_button")]')
COMMIT_MESSAGE_TEXT = (
    u'//div[@id="edit-commit_message"]//div[@class="yui3-editable_text-text"]')


class TestCommitMessage(WindmillTestCase):

    layer = CodeWindmillLayer
    suite_name = "Commit message editing."

    def test_set_commit_message(self):
        """Test the commit message multiline editor."""
        eric = self.factory.makePerson(
            name="eric", displayname="Eric the Viking", password="test",
            email="eric@example.com")
        bmp = self.factory.makeBranchMergeProposal(registrant=eric)
        transaction.commit()

        client, start_url = self.getClientForPerson(bmp, eric)

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
        client.open(url=start_url)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        client.asserts.assertText(
            xpath=COMMIT_MESSAGE_TEXT, validator=message)


class TestQueueStatus(WindmillTestCase):

    layer = CodeWindmillLayer
    suite_name = "Queue status setting"

    def test_inline_queue_status_setting(self):
        """Test setting the queue_status with the ChoiceWidget."""
        mike = self.factory.makePerson(
            name="mike", displayname="Mike Tyson", password="test",
            email="mike@example.com")
        branch = self.factory.makeBranch(owner=mike)
        second_branch = self.factory.makeBranch(product=branch.product)
        self.factory.makeRevisionsForBranch(second_branch)
        merge_proposal = second_branch.addLandingTarget(mike, branch)
        transaction.commit()

        client, start_url = self.getClientForPerson(merge_proposal, mike)

        # Click on the element containing the branch status.
        client.waits.forElement(
            id=u'branchmergeproposal-status-value', timeout=PAGE_LOAD)
        client.click(id=u'branchmergeproposal-status-value')
        client.waits.forElement(
            xpath=u'//div[contains(@class, "yui3-ichoicelist-content")]')

        # Change the status to experimental.
        client.click(link=u'Approved')
        client.waits.sleep(milliseconds=SLEEP)

        client.asserts.assertText(
            xpath=u'//td[@id="branchmergeproposal-status-value"]/a',
            validator=u'Approved')

        client.asserts.assertText(
            xpath=u'//tr[@id="summary-row-3-approved-revision"]/td',
            validator=u'5')

        # Reload the page and make sure the change sticks.
        client.open(url=start_url)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        client.waits.forElement(
            xpath=u'//td[@id="branchmergeproposal-status-value"]/a',
            timeout=FOR_ELEMENT)
        client.asserts.assertText(
            xpath=u'//td[@id="branchmergeproposal-status-value"]/a',
            validator=u'Approved')
