# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test for branch subscriptions."""

__metaclass__ = type
__all__ = []

import windmill
from windmill.authoring import WindmillTestClient

from canonical.launchpad.windmill.testing import lpuser


# XXX: rockstar - Also needs testing : Admins can edit/delete, members of the
# team can edit/delete.  At least the latter will require the Launchpad object
# factory.

def test_branch_subscription_ajax_load():
    """Test branch subscriptions loaded via ajax."""
    client = WindmillTestClient("Branch Subscription Ajax Load Test")

    lpuser.FOO_BAR.ensure_login(client)

    client.open(
        url=windmill.settings['TEST_URL'] + '/~sabdfl/firefox/release--0.9.1')
    client.waits.forElement(id=u'none-subscribers', timeout=u'10000')
    client.asserts.assertText(id=u'none-subscribers',
        validator=u'No subscribers.')

    client.click(id=u'selfsubscription')
    client.waits.forPageLoad(timeout=u'100000')
    client.click(id=u'field.actions.subscribe')

    client.waits.forElement(id=u'editsubscription-icon-name16',
        timeout=u'10000')
    client.asserts.assertText(id=u'subscriber-name16',
        validator=u'Foo Bar')
    client.click(id=u'editsubscription-icon-name16')

    client.waits.forPageLoad(timeout=u'100000')
    client.click(id=u'field.actions.unsubscribe')

    client.waits.forElement(id=u'none-subscribers', timeout=u'10000')
    client.asserts.assertText(id=u'none-subscribers',
        validator=u'No subscribers.')


def test_team_edit_subscription_ajax_load():
    """Test that team subscriptions are editable through the ajax portlet."""
    client = WindmillTestClient("Branch Subscription Ajax Load Test")

    lpuser.SAMPLE_PERSON.ensure_login(client)

    client.open(
        url=windmill.settings['TEST_URL'] + '/~name12/landscape/feature-x/')
    client.waits.forPageLoad(timeout=u'10000')

    client.waits.forElement(id=u'editsubscription-icon-landscape-developers',
        timeout=u'10000')
    client.asserts.assertText(id=u'subscriber-landscape-developers',
        validator=u'Landscape Developers')
    client.click(id=u'editsubscription-icon-landscape-developers')

    client.waits.forPageLoad(timeout=u'100000')
    client.click(id=u'field.actions.unsubscribe')

    client.waits.forElement(id=u'none-subscribers', timeout=u'10000')
    client.asserts.assertText(id=u'none-subscribers',
        validator=u'No subscribers.')
