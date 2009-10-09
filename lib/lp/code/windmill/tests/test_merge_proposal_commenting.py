# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for the inline commenting UI."""

__metaclass__ = type
__all__ = []

import unittest

import transaction
from zope.security.proxy import removeSecurityProxy
import windmill
from windmill.authoring import WindmillTestClient

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.windmill.testing import lpuser
from canonical.uuid import generate_uuid
from lp.code.windmill.testing import CodeWindmillLayer
from lp.testing import TestCaseWithFactory

WAIT_PAGELOAD = u'30000'
WAIT_ELEMENT_COMPLETE = u'30000'
WAIT_CHECK_CHANGE = u'1000'
ADD_COMMENT_BUTTON = (
    u'//input[@id="field.actions.add" and @class="button js-action"]')


class TestMergeProposalCommenting(TestCaseWithFactory):

    layer = CodeWindmillLayer

    @staticmethod
    def canonical_url(lp_object):
        url = canonical_url(lp_object)
        url = url.replace(
            'http://code.launchpad.dev', windmill.settings['TEST_URL'])
        assert url.startswith(windmill.settings['TEST_URL'])
        return url

    def test_merge_proposal_commenting(self):
        """Test commenting on bugs."""
        client = WindmillTestClient('Bug commenting')
        lpuser.NO_PRIV.ensure_login(client)

        proposal = self.factory.makeBranchMergeProposal()
        transaction.commit()
        #raise Exception(repr(url))
        client.open(url=self.canonical_url(proposal))
        client.waits.forPageLoad(timeout=WAIT_PAGELOAD)
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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
