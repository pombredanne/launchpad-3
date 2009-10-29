# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for the main branch page."""

__metaclass__ = type
__all__ = []

import transaction
import unittest

import windmill
from windmill.authoring import WindmillTestClient

from canonical.launchpad.windmill.testing.constants import (
    PAGE_LOAD, SLEEP)
from canonical.launchpad.windmill.testing.lpuser import login_person
from lp.code.windmill.testing import CodeWindmillLayer
from lp.testing import TestCaseWithFactory


class TestBranchStatus(TestCaseWithFactory):

    layer = CodeWindmillLayer

    def test_inline_branch_status_setting(self):
        """Test branch bug links."""
        eric = self.factory.makePerson(
            name="eric", displayname="Eric the Viking", password="test",
            email="eric@example.com")
        branch = self.factory.makeBranch(owner=eric)
        transaction.commit()

        client = WindmillTestClient("Branch status setting")

        start_url = (
            windmill.settings['TEST_URL'] + branch.unique_name)
        client.open(url=start_url)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        login_person(eric, "test", client)

        # Click on the element containing the branch status.
        client.waits.forElement(
            id=u'branch-details-status-value', timeout=PAGE_LOAD)
        client.click(id=u'branch-details-status-value')
        client.waits.forElement(
            xpath=u'//div[contains(@class, "yui-ichoicelist-content")]')

        # Change the status to experimental.
        client.click(link=u'Experimental')
        client.waits.sleep(milliseconds=SLEEP)

        client.asserts.assertText(
            xpath=u'//span[@id="branch-details-status-value"]/span',
            validator=u'Experimental')

        # Reload the page and make sure the change sticks.
        client.open(url=start_url)
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        client.waits.forElement(
            xpath=u'//span[@id="branch-details-status-value"]/span',
            timeout=constants.FOR_ELEMENT)
        client.asserts.assertText(
            xpath=u'//span[@id="branch-details-status-value"]/span',
            validator=u'Experimental')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
