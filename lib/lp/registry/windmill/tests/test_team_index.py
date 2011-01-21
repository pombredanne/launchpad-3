# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test team index page."""

__metaclass__ = type
__all__ = []

import unittest

from canonical.launchpad.windmill.testing import lpuser
from canonical.launchpad.windmill.testing.widgets import (
    search_and_select_picker_widget,
    )
from lp.registry.windmill.testing import RegistryWindmillLayer
from lp.testing import WindmillTestCase


class TestTeamIndex(WindmillTestCase):
    """Test team index page."""

    layer = RegistryWindmillLayer
    suite_name = __name__

    def test_addmember(self):
        self.client.open(
            url=u'%s/~testing-spanish-team' % RegistryWindmillLayer.base_url)

        lpuser.TRANSLATIONS_ADMIN.ensure_login(self.client)

        addmember_xpath = (
            '//*[@id="membership"]' +
            '//a[text()="Add member" ' +
            'and contains(@class, "js-action")]')
        # Add rosetta-admins team as a member.
        approved_count_xpath = '//*[@id="approved-member-count"]'
        code = "lookupNode({xpath: '%s'}).textContent" % approved_count_xpath
        result = self.client.commands.execJS(code=code)
        old_approved_count = int(result['result'])

        self.client.waits.forElement(xpath=addmember_xpath)
        self.client.click(xpath=addmember_xpath)
        # Xpath is 1-indexed.
        search_and_select_picker_widget(self.client, 'rosetta', 1)

        self.client.waits.forElement(
            xpath='//ul[@id="recently-approved-ul"]/li[1]/a',
            option='href|~rosetta-admins')

        self.client.asserts.assertText(
            xpath=approved_count_xpath,
            validator=str(old_approved_count+1))

        # Add another team as a member.
        invited_count_xpath = '//*[@id="invited-member-count"]'
        self.client.asserts.assertNotNode(xpath=invited_count_xpath)
        self.client.click(xpath=addmember_xpath)
        search_and_select_picker_widget(self.client, 'simple', 1)

        self.client.waits.forElement(
            xpath='//ul[@id="recently-invited-ul"]/li[1]/a',
            option='href|~simple-team')

        self.client.asserts.assertText(
            xpath=invited_count_xpath,
            validator="1")

        # Verify that there is now a relative link to
        # "+members#invited", which is equivalent to
        # "~testing-spanish-team/+members#invited".
        self.client.asserts.assertNode(
            xpath='//*[@id="membership-counts"]'
                  '//a[@href="+members#invited"]')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
