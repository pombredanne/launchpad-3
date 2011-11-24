# Copyright 2009-2010 Canonical Ltd.  All rights reserved.

"""Test for code review."""

__metaclass__ = type
__all__ = []

from uuid import uuid1

import transaction

from canonical.launchpad.webapp import canonical_url
from lp.code.windmill.testing import CodeWindmillLayer
from lp.testing import (
    login_person,
    WindmillTestCase,
    )
from lp.testing.windmill import (
    constants,
    lpuser,
    )
from lp.testing.windmill.widgets import (
    search_and_select_picker_widget,
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

        client, start_url = self.getClientFor(
            '/~name12/gnome-terminal/klingon/', lpuser.FOO_BAR)

        link = u'//a[@class="menu-link-register_merge sprite add"]'
        client.waits.forElement(xpath=link, timeout=constants.FOR_ELEMENT)
        client.click(xpath=link)
        client.type(text=u'~name12/gnome-terminal/main',
            id=u'field.target_branch.target_branch')

        # Check that the javascript to disable the review_type field when the
        # reviewer field is empty works.
        client.asserts.assertProperty(
            id=u"field.review_type", validator='disabled|true')
        # User types into reviewer field manually.
        client.type(text=u'mark', id=u'field.reviewer')
        client.asserts.assertProperty(
            id=u"field.review_type", validator='disabled|false')
        client.type(text=u'', id=u'field.reviewer')
        client.asserts.assertProperty(
            id=u"field.review_type", validator='disabled|true')
        # User selects reviewer using popup selector widget.
        client.click(id=u'show-widget-field-reviewer')
        search_and_select_picker_widget(client, u'name12', 1)
        # Tab out of the field.
        client.keyPress(
            options='\\9,true,false,false,false,false',
            id=u'field.reviewer')
        # Give javascript event handler time to run
        client.waits.sleep(milliseconds=unicode(500))
        client.asserts.assertProperty(
            id=u"field.review_type", validator='disabled|false')

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
        client, start_url = self.getClientFor('/', lpuser.NO_PRIV)

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
        client, start_url = self.getClientFor('/', lpuser.NO_PRIV)
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
        client, start_url = self.getClientFor('/', lpuser.NO_PRIV)
        proposal = self.factory.makeBranchMergeProposal()
        self.open_proposal_page(client, proposal)
        client.waits.forElement(xpath=ADD_COMMENT_BUTTON)

        new_comment_text = str(uuid1())
        client.type(text=new_comment_text, id="field.comment")
        client.select(id=u'field.vote', val=u'APPROVE')
        client.click(xpath=ADD_COMMENT_BUTTON)
        client.waits.forElement(id=u'review-no-priv', timeout=u'40000')
