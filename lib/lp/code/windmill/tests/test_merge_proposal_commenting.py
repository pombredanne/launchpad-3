# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for the inline commenting UI."""

__metaclass__ = type
__all__ = []

import unittest

import transaction
from windmill.authoring import WindmillTestClient

from canonical.launchpad.windmill.testing import lpuser
from canonical.uuid import generate_uuid
from lp.code.windmill.testing import canonical_url, CodeWindmillLayer
from lp.testing import login_person, TestCaseWithFactory

WAIT_PAGELOAD = u'30000'
WAIT_ELEMENT_COMPLETE = u'30000'
WAIT_CHECK_CHANGE = u'1000'
ADD_COMMENT_BUTTON = (
    u'//input[@id="field.actions.add" and @class="button js-action"]')


class TestMergeProposalCommenting(TestCaseWithFactory):

    layer = CodeWindmillLayer


    def open_proposal_page(self, client, proposal):
        transaction.commit()
        client.open(url=canonical_url(proposal))
        client.waits.forPageLoad(timeout=WAIT_PAGELOAD)

    def test_merge_proposal_commenting(self):
        """Test commenting on merge proposals."""
        client = WindmillTestClient('Code review commenting')
        lpuser.NO_PRIV.ensure_login(client)

        proposal = self.factory.makeBranchMergeProposal()
        self.open_proposal_page(client, proposal)
        client.waits.forElement(xpath=ADD_COMMENT_BUTTON)
        # Generate a unique piece of text, so we can run the test multiple
        # times, without resetting the db.
        new_comment_text = generate_uuid()
        client.type(text=new_comment_text, id="field.comment")
        client.click(xpath=ADD_COMMENT_BUTTON)
        # A PRE inside a boardCommentBody, itself somewhere in the
        # #conversation
        client.waits.forElement(
            xpath='//div[@id="conversation"]//div[@class="boardCommentBody"]'
            '/pre[contains(., "%s")]' % new_comment_text)

    def test_merge_proposal_replying(self):
        """Replying to code review comments works."""
        client = WindmillTestClient('Code review commenting')
        lpuser.NO_PRIV.ensure_login(client)
        proposal = self.factory.makeBranchMergeProposal()
        login_person(proposal.registrant)
        proposal.createComment(proposal.registrant, 'hello', 'content')
        self.open_proposal_page(client, proposal)
        REPLY_LINK_XPATH = '//a[contains(., "Reply")]'
        client.waits.forElement(xpath=REPLY_LINK_XPATH)
        client.click(xpath=REPLY_LINK_XPATH)
        client.waits.sleep(milliseconds=10)
        client.asserts.assertValue(id="field.comment", validator="> content")
        new_comment_text = generate_uuid()
        client.type(text=new_comment_text, id="field.comment")
        client.click(xpath=ADD_COMMENT_BUTTON)
        client.waits.forElement(
            xpath='//div[@id="conversation"]//div[@class="boardCommentBody"]'
            '/pre[contains(., "%s")]' % new_comment_text)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
