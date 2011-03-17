# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for the bug tag entry UI."""

__metaclass__ = type
__all__ = []

import unittest
from uuid import uuid1

from lp.bugs.windmill.testing import BugsWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill import lpuser


WAIT_PAGELOAD = u'30000'
WAIT_ELEMENT_COMPLETE = u'30000'
WAIT_CHECK_CHANGE = u'1000'
ADD_COMMENT_BUTTON = (
    u'//input[@id="field.actions.save" and contains(@class, "button")]')


class TestBugCommenting(WindmillTestCase):

    layer = BugsWindmillLayer
    suite_name = 'Bug commenting'

    def test_bug_commenting(self):
        """Test commenting on bugs."""
        client = self.client
        lpuser.NO_PRIV.ensure_login(client)

        client.open(url='%s/bugs/1' % BugsWindmillLayer.base_url)
        client.waits.forPageLoad(timeout=WAIT_PAGELOAD)
        client.waits.forElement(xpath=ADD_COMMENT_BUTTON)

        # Generate a unique piece of text, so we can run the test multiple
        # times, without resetting the db.
        new_comment_text = str(uuid1())
        client.type(text=new_comment_text, id="field.comment")
        client.click(xpath=ADD_COMMENT_BUTTON)
        client.waits.forElement(
            xpath=u'//div[@class="bug-comment"]/p[contains(., "%s")]' % (
                new_comment_text))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
