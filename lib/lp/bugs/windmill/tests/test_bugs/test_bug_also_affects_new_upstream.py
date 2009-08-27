# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from canonical.launchpad.windmill.testing.widgets import (
    FormPickerWidgetTest)
from canonical.launchpad.windmill.testing import lpuser
from canonical.launchpad.windmill.testing.widgets import search_picker_widget
from canonical.launchpad.windmill.testing.constants import (
    PAGE_LOAD, FOR_ELEMENT, SLEEP)

from windmill.authoring import WindmillTestClient

CHOOSE_AFFECTED_URL = ('http://bugs.launchpad.dev:8085/tomcat/+bug/3/'
                       '+choose-affected-product')

test_bug_also_affects_picker = FormPickerWidgetTest(
    name='test_bug_also_affects',
    url=CHOOSE_AFFECTED_URL,
    short_field_name='product',
    search_text='firefox',
    result_index=1,
    new_value='firefox')

def test_bug_also_affects_register_link():
    """Test that picker shows "Register it" link.

    Sometimes users want to indicate that a bug also affects another upstream
    but then they realize that upstream is not yet registered in Launchpad. In
    order to make their life easier, we allow them to register a new upstream
    and indicate that it's affected by a given bug, all at once.
    """
    choose_link_id = 'show-widget-field-product'
    client = WindmillTestClient('test_bug_also_affects_register_link')

    lpuser.SAMPLE_PERSON.ensure_login(client)

    # Open a bug page and wait for it to finish loading.
    client.open(url=CHOOSE_AFFECTED_URL)
    client.waits.forPageLoad(timeout=PAGE_LOAD)
    client.click(id=choose_link_id)
    search_picker_widget(client, 'nonexistant')
    client.asserts.assertProperty(
        xpath=(u"//table[contains(@class, 'yui-picker') "
                "and not(contains(@class, 'yui-picker-hidden'))]"
                "//div[contains(@class, 'yui-picker-footer-slot')]"
                "//a"),
        validator=u'href|/tomcat/+bug/3/+affects-new-product')
