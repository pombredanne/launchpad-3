# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test for code review."""

__metaclass__ = type
__all__ = []

import unittest

import windmill
from windmill.authoring import WindmillTestClient

from canonical.launchpad.windmill.testing import lpuser
from canonical.launchpad.windmill.testing.widgets import (
    search_and_select_picker_widget)
from lp.code.windmill.testing import CodeWindmillLayer
from lp.testing import TestCaseWithFactory


class TestCodeReview(TestCaseWithFactory):
    """Test the javascript functions of code review."""

    layer = CodeWindmillLayer

    def test_inline_request_a_reviewer(self):
        """Test inline request a reviewer."""

        client = WindmillTestClient("Code review")

        lpuser.FOO_BAR.ensure_login(client)

        client.open(url=''.join([
            windmill.settings['TEST_URL'],
            '/~name12/gnome-terminal/klingon/']))
        client.waits.forPageLoad(timeout=u'10000')

        link = u'//a[@class="menu-link-register_merge sprite merge-proposal"]'
        client.click(xpath=link)
        client.type(text=u'~name12/gnome-terminal/main',
            id=u'field.target_branch.target_branch')
        client.click(id=u'field.actions.register')

        client.waits.forPageLoad(timeout=u'10000')
        client.click(id=u'request-review')

        search_and_select_picker_widget(client, u'mark', 1)

        client.waits.forElement(id=u'review-mark', timeout=u'10000')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
