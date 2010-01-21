# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test for code review."""

__metaclass__ = type
__all__ = []

import unittest

import transaction
import windmill
from windmill.authoring import WindmillTestClient

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.windmill.testing import lpuser
from canonical.launchpad.windmill.testing.widgets import (
    search_and_select_picker_widget)
from canonical.uuid import generate_uuid
from lp.code.windmill.testing import CodeWindmillLayer
from lp.testing import login_person, TestCaseWithFactory

WAIT_PAGELOAD = u'30000'
WAIT_ELEMENT_COMPLETE = u'30000'
WAIT_CHECK_CHANGE = u'1000'
ADD_COMMENT_BUTTON = (
    u'//input[@id="field.actions.add" and @class="button js-action"]')


class TestRequestReview(TestCaseWithFactory):
    """Test the javascript functions of code review."""

    layer = CodeWindmillLayer

    def test_inline_request_a_reviewer(self):
        """Request a review."""

        client = WindmillTestClient("Code review")

        lpuser.FOO_BAR.ensure_login(client)

        client.open(url=''.join([
            windmill.settings['TEST_URL'],
            '/~name12/gnome-terminal/klingon/']))
        client.waits.forPageLoad(timeout=u'10000')

        link = u'//a[@class="menu-link-register_merge sprite add"]'
        client.click(xpath=link)
        client.type(text=u'~name12/gnome-terminal/main',
            id=u'field.target_branch.target_branch')
        client.click(id=u'field.actions.register')

        client.waits.forPageLoad(timeout=u'10000')
        client.click(id=u'request-review')

        search_and_select_picker_widget(client, u'mark', 1)

        client.waits.forElement(id=u'review-mark', timeout=u'10000')


class TestReviewCommenting(TestCaseWithFactory):
    """Test commenting and reviewing on a merge proposal."""

    layer = CodeWindmillLayer

    def open_proposal_page(self, client, proposal):
        transaction.commit()
        client.open(url=canonical_url(proposal))
        client.waits.forPageLoad(timeout=WAIT_PAGELOAD)

    def test_merge_proposal_commenting(self):
        """Comment on a merge proposal."""
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
        """Reply to a review comment."""
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
        new_comment_text = "My reply"
        client.type(text=new_comment_text, id="field.comment")
        client.click(xpath=ADD_COMMENT_BUTTON)
        client.waits.forElement(
            xpath='//div[@id="conversation"]//div[@class="boardCommentBody"]'
            '/pre[contains(., "%s")]' % new_comment_text)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
