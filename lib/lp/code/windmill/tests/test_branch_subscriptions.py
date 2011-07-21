# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for branch subscriptions."""

__metaclass__ = type
__all__ = []

import windmill

from lp.code.windmill.testing import CodeWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill import lpuser


class TestBranchSubscriptions(WindmillTestCase):
    """Test subscriptions to branches."""

    layer = CodeWindmillLayer
    suite_name = "Branch Subscription Ajax Load Test"

    def test_branch_subscription_ajax_load(self):
        """Subscribe to a branch from the branch page."""

        client, start_url = self.getClientFor(
            '/~mark/firefox/release--0.9.1', lpuser.FOO_BAR)
        client.waits.forElement(id=u'none-subscribers', timeout=u'10000')
        client.asserts.assertText(
            xpath=u'//a[@class="sprite add subscribe-self js-action"]',
            validator='Subscribe yourself')
        client.asserts.assertText(id=u'none-subscribers',
            validator=u'No subscribers.')

        client.click(
            xpath=u'//a[@class="sprite add subscribe-self js-action"]')
        client.waits.forElement(id=u'yui3-pretty-overlay-modal')
        client.click(xpath=u'//button[@name="field.actions.subscribe"]')

        client.waits.forElement(id=u'editsubscription-icon-name16',
            timeout=u'10000')
        client.asserts.assertText(id=u'subscriber-name16',
            validator=u'Foo Bar')

        # And now to unsubscribe
        client.click(id=u'editsubscription-icon-name16')

        client.waits.forPageLoad(timeout=u'100000')
        client.click(id=u'field.actions.unsubscribe')

        client.waits.forElement(id=u'none-subscribers', timeout=u'10000')
        client.asserts.assertText(id=u'none-subscribers',
            validator=u'No subscribers.')

    def test_team_edit_subscription_ajax_load(self):
        """Unsubscribe a team from the branch."""

        client, start_url = self.getClientFor(
            '/~name12/landscape/feature-x/', lpuser.SAMPLE_PERSON)
        client.waits.forElement(
            id=u'editsubscription-icon-landscape-developers',
            timeout=u'10000')

        client.asserts.assertText(id=u'subscriber-landscape-developers',
            validator=u'Landscape Developers')
        client.click(id=u'editsubscription-icon-landscape-developers')

        client.waits.forPageLoad(timeout=u'100000')
        client.click(id=u'field.actions.unsubscribe')

        client.waits.forElement(id=u'none-subscribers', timeout=u'10000')
        client.asserts.assertText(id=u'none-subscribers',
            validator=u'No subscribers.')
