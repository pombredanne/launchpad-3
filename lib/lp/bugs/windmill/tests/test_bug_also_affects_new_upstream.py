# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import unittest

from canonical.launchpad.windmill.testing.widgets import (
    FormPickerWidgetTest)
from canonical.launchpad.windmill.testing import lpuser, constants
from canonical.launchpad.windmill.testing.widgets import search_picker_widget
from lp.bugs.windmill.testing import BugsWindmillLayer
from lp.testing import WindmillTestCase

CHOOSE_AFFECTED_URL = ('http://bugs.launchpad.dev:8085/tomcat/+bug/3/'
                       '+choose-affected-product')

class TestBugAlsoAffects(WindmillTestCase):

    layer = BugsWindmillLayer
    suite_name = 'test_bug_also_affects_register_link'

    test_bug_also_affects_picker = FormPickerWidgetTest(
        name='test_bug_also_affects',
        url=CHOOSE_AFFECTED_URL,
        short_field_name='product',
        search_text='firefox',
        result_index=1,
        new_value='firefox')

    def test_bug_also_affects_register_link(self):
        """Test that picker shows "Register it" link.

        Sometimes users want to indicate that a bug also affects another upstream
        but then they realize that upstream is not yet registered in Launchpad. In
        order to make their life easier, we allow them to register a new upstream
        and indicate that it's affected by a given bug, all at once.
        """

        choose_link_id = 'show-widget-field-product'
        client = self.client

        # Open a bug page and wait for it to finish loading.
        client.open(url=CHOOSE_AFFECTED_URL)
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        lpuser.SAMPLE_PERSON.ensure_login(client)

        client.waits.forElement(
            id=choose_link_id, timeout=constants.FOR_ELEMENT)
        client.click(id=choose_link_id)
        search_picker_widget(client, 'nonexistant')
        client.waits.forElement(
            link=u'Register it', timeout=constants.FOR_ELEMENT)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
