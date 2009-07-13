# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test for branch links."""

__metaclass__ = type
__all__ = []

import windmill
from windmill.authoring import WindmillTestClient

from canonical.launchpad.windmill.testing import lpuser


def test_inline_branch_bug_link_unlink():
    """Test branch bug links."""
    client = WindmillTestClient("Branch bug links")

    lpuser.FOO_BAR.ensure_login(client)

    client.open(
        url=windmill.settings['TEST_URL'] + '/~sabdfl/firefox/release--0.9.1')
    client.waits.forElement(id=u'linkbug', timeout=u'10000')
    client.click(id=u'linkbug')

    client.waits.forElement(id=u'field.bug')
    client.type(text=u'1', id=u'field.bug')
    client.click(xpath=u'//button[@name="buglink.actions.change"]')

    client.waits.forElement(id=u'buglink-1', timeout=u'10000')
    client.asserts.assertText(id=u'linkbug',
        validator=u'Link to another bug')

    client.click(id=u'linkbug')
    client.waits.forElement(id=u'field.bug')
    client.type(text=u'2', id=u'field.bug')
    client.click(xpath=u'//button[@name="buglink.actions.change"]')

    client.waits.forElement(id=u'buglink-1', timeout=u'10000')
    client.asserts.assertText(id=u'linkbug',
        validator=u'Link to another bug')

    # And now to unlink.
    client.click(id=u'delete-buglink-1')
    client.waits.sleep(milliseconds=3000)
    client.asserts.assertNotNode(id=u'buglink-1')
    client.click(id=u'delete-buglink-2')
    client.waits.sleep(milliseconds=3000)
    client.asserts.assertNotNode(id=u'buglink-2')
    client.asserts.assertText(id=u'linkbug',
        validator=u'Link to a bug report')

