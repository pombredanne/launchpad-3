# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from lp.bugs.windmill.testing import BugsWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill import (
    constants,
    lpuser,
    )
from lp.testing.windmill.widgets import (
    FormPickerWidgetTest,
    search_picker_widget,
    )


class TestBugAlsoAffects(WindmillTestCase):

    layer = BugsWindmillLayer
    suite_name = 'test_bug_also_affects_register_link'

    def setUp(self):
        WindmillTestCase.setUp(self)
        self.client, start_url = self.getClientFor(
            '/', user=lpuser.SAMPLE_PERSON)
        self.choose_affected_url = (
                            '%s/tomcat/+bug/3/+choose-affected-product'
                            % BugsWindmillLayer.base_url)

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
        client.open(url=self.choose_affected_url)
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)

        client.waits.forElement(
            id=choose_link_id, timeout=constants.FOR_ELEMENT)
        client.click(id=choose_link_id)
        search_picker_widget(client, 'nonexistant')
        client.waits.forElement(
            link=u'Register it', timeout=constants.FOR_ELEMENT)
