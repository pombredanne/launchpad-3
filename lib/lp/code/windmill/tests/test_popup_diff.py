# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for the popup diff."""

__metaclass__ = type
__all__ = []

import transaction
import unittest

import windmill
from windmill.authoring import WindmillTestClient

from canonical.launchpad.windmill.testing.constants import PAGE_LOAD
from lp.code.tests.helpers import make_erics_fooix_project
from lp.code.windmill.testing import CodeWindmillLayer
from lp.testing import TestCaseWithFactory


POPUP_DIFF = u'//dd[contains(@class, "popup-diff")]/a'
VISIBLE_DIFF = (
    u'//table[contains(@class, "yui-diff-overlay") and '
     'not(contains(@class, "yui-diff-overlay-hidden"))]')
CLOSE_VISIBLE_DIFF = (
    u'//table[contains(@class, "yui-diff-overlay")]'
     '//a[@class="close-button"]')


class TestPopupOnBranchPage(TestCaseWithFactory):
    """Test the popup diff."""

    layer = CodeWindmillLayer

    def test_inline_branch_bug_link_unlink(self):
        """Test branch diff popups."""
        client = WindmillTestClient("Branch popup diffs")
        make_erics_fooix_project(self.factory)
        transaction.commit()

        start_url = (
            windmill.settings['TEST_URL'] + '/~fred/fooix/proposed')
        client.open(url=start_url)
        client.waits.forPageLoad(timeout=PAGE_LOAD)

        client.click(xpath=POPUP_DIFF)
        # Wait for the diff to show.
        client.waits.forElement(xpath=VISIBLE_DIFF)
        # Click on the close button.
        client.click(xpath=CLOSE_VISIBLE_DIFF)
        # Make sure that the diff has gone.
        client.asserts.assertNotNode(xpath=VISIBLE_DIFF)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
