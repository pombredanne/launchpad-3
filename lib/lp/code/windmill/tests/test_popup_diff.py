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
from lp.bugs.windmill.testing import BugsWindmillLayer
from lp.code.tests.helpers import make_erics_fooix_project
from lp.code.windmill.testing import CodeWindmillLayer
from lp.testing import TestCaseWithFactory


POPUP_DIFF = (
    u'//dd[contains(@class, "popup-diff")]'
    '/a[contains(@class, "js-action")]')
VISIBLE_DIFF = (
    u'//table[contains(@class, "yui-diff-overlay") and '
     'not(contains(@class, "yui-diff-overlay-hidden"))]')
CLOSE_VISIBLE_DIFF = (
    u'//table[contains(@class, "yui-diff-overlay")]'
     '//a[@class="close-button"]')
JS_ONLOAD_EXECUTE_DELAY = 2000


class TestPopupOnBranchPage(TestCaseWithFactory):
    """Test the popup diff."""

    layer = CodeWindmillLayer

    def test_branch_popup_diff(self):
        """Test branch diff popups."""
        client = WindmillTestClient("Branch popup diffs")
        make_erics_fooix_project(self.factory)
        transaction.commit()

        start_url = (
            windmill.settings['TEST_URL'] + '~fred/fooix/proposed')
        client.open(url=start_url)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        # Sleep for a bit to make sure that the JS onload has had time to execute.
        client.waits.sleep(milliseconds=JS_ONLOAD_EXECUTE_DELAY)

        # Make sure that the link anchor has the js-action class.
        client.asserts.assertNode(xpath=POPUP_DIFF)
        client.click(xpath=POPUP_DIFF)

        # Wait for the diff to show.
        client.waits.forElement(xpath=VISIBLE_DIFF)
        # Click on the close button.
        client.click(xpath=CLOSE_VISIBLE_DIFF)
        # Make sure that the diff has gone.
        client.asserts.assertNotNode(xpath=VISIBLE_DIFF)


class TestPopupOnBugPage(TestCaseWithFactory):
    """Test the popup diff for bug pages.

    Need this to be in the BugsWindmillLayer to run from the right subdomain.
    """

    layer = BugsWindmillLayer

    def test_bug_popup_diff(self):
        """Test bug page diff popups."""
        client = WindmillTestClient("Bug popup diffs")
        objs = make_erics_fooix_project(self.factory)
        bug = self.factory.makeBug(product=objs['fooix'])
        bug.linkBranch(objs['proposed'], objs['fred'])
        transaction.commit()

        start_url = (windmill.settings['TEST_URL'] + 'bugs/%d' % bug.id)
        client.open(url=start_url)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        # Sleep for a bit to make sure that the JS onload has had time to execute.
        client.waits.sleep(milliseconds=JS_ONLOAD_EXECUTE_DELAY)

        # Make sure that the link anchor has the js-action class.
        client.asserts.assertNode(xpath=POPUP_DIFF)
        client.click(xpath=POPUP_DIFF)

        # Wait for the diff to show.
        client.waits.forElement(xpath=VISIBLE_DIFF)
        # Click on the close button.
        client.click(xpath=CLOSE_VISIBLE_DIFF)
        # Make sure that the diff has gone.
        client.asserts.assertNotNode(xpath=VISIBLE_DIFF)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
