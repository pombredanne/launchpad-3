# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test for code review."""

__metaclass__ = type
__all__ = []

import windmill
from windmill.authoring import WindmillTestClient

from canonical.launchpad.windmill.testing import lpuser
from canonical.launchpad.windmill.testing.widgets import (
    _search_picker_widget)


MERGE_LINK = '%s/~name12/gnome-terminal/klingon/+register-merge' % (
    windmill.settings['TEST_URL'])

def test_inline_request_a_reviewer():
    """Test inline request a reviewer."""
    client = WindmillTestClient("Code review")

    lpuser.FOO_BAR.ensure_login(client)

    client.open(
        url=windmill.settings['TEST_URL'] + '/~name12/gnome-terminal/klingon/')
    client.waits.forPageLoad(timeout=u'10000')

    client.click(xpath=u'//a[@href="%s"]' % MERGE_LINK)
    client.type(text=u'~name12/gnome-terminal/main',
        id=u'field.target_branch.target_branch')
    client.click(id=u'field.actions.register')

    client.waits.forPageLoad(timeout=u'10000')
    client.click(id=u'request-review')

    _search_picker_widget(client, u'sabdfl', 1)

    client.waits.forElement(id=u'review-sabdfl', timeout=u'10000')
