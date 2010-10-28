# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test for code review."""

__metaclass__ = type
__all__ = []

import unittest
from uuid import uuid1

import transaction
import windmill

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.windmill.testing import lpuser
from canonical.launchpad.windmill.testing.widgets import (
    search_and_select_picker_widget,
    )
from lp.code.windmill.testing import CodeWindmillLayer
from lp.testing import (
    login_person,
    WindmillTestCase,
    )


WAIT_PAGELOAD = u'30000'
WAIT_ELEMENT_COMPLETE = u'30000'
WAIT_CHECK_CHANGE = u'1000'
ADD_COMMENT_BUTTON = (
    u'//input[@id="field.actions.add" and contains(@class, "button")]')


class TestRequestReview(WindmillTestCase):
    """Test the javascript functions of code review."""

    layer = CodeWindmillLayer
    suite_name = "Code review"

    def test_inline_request_a_reviewer(self):
        """Request a review."""

        client = self.client

        lpuser.FOO_BAR.ensure_login(client)

        client.open(url=''.join([
            windmill.settings['TEST_URL'],
            '~name12/gnome-terminal/klingon/']))
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


class TestReviewCommenting(WindmillTestCase):
    """Test commenting and reviewing on a merge proposal."""

    layer = CodeWindmillLayer
    suite_name = 'Code review commenting'

    def open_proposal_page(self, client, proposal):
        transaction.commit()
        client.open(url=canonical_url(proposal))
        client.waits.forPageLoad(timeout=WAIT_PAGELOAD)

    def test_merge_proposal_commenting(self):
        """Comment on a merge proposal."""
        client = self.client
        lpuser.NO_PRIV.ensure_login(client)

        proposal = self.factory.makeBranchMergeProposal()
        self.open_proposal_page(client, proposal)
        client.waits.forElement(xpath=ADD_COMMENT_BUTTON)
        # Generate a unique piece of text, so we can run the test multiple
        # times, without resetting the db.
        new_comment_text = str(uuid1())
        client.type(text=new_comment_text, id="field.comment")
        client.click(xpath=ADD_COMMENT_BUTTON)
        # A PRE inside a boardCommentBody, itself somewhere in the
        # #conversation
        client.waits.forElement(
            xpath='//div[@id="conversation"]//div[@class="boardCommentBody"]'
            '/pre[contains(., "%s")]' % new_comment_text)

    def test_merge_proposal_replying(self):
        """Reply to a review comment."""
        client = self.client
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

    def test_merge_proposal_reviewing(self):
        """Comment on a merge proposal."""
        client = self.client
        lpuser.NO_PRIV.ensure_login(client)

        proposal = self.factory.makeBranchMergeProposal()
        self.open_proposal_page(client, proposal)
        client.waits.forElement(xpath=ADD_COMMENT_BUTTON)

        new_comment_text = str(uuid1())
        client.type(text=new_comment_text, id="field.comment")
        client.select(id=u'field.vote', val=u'APPROVE')
        client.click(xpath=ADD_COMMENT_BUTTON)
        client.waits.forElement(id=u'review-no-priv', timeout=u'40000')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
