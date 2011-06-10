# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from lp.bugs.windmill.testing import BugsWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill import (
    constants,
    lpuser,
    )


class TestFilebugExtras(WindmillTestCase):

    layer = BugsWindmillLayer
    suite_name = "File bug extra options test"

    def test_filebug_extra_options(self):
        """Test the extra options area on +filebug pages.

        This test ensures that, with Javascript enabled, the extra options
        expander starts closed, and contains several fields when opened.
        """

        # Open a +filebug page and wait for it to finish loading.
        client, start_url = self.getClientFor(
            '/firefox/+filebug', user=lpuser.SAMPLE_PERSON)

        # Search for a possible duplicate.
        client.waits.forElement(
            id=u'field.search', timeout=constants.FOR_ELEMENT)
        client.type(text=u'Broken', id=u'field.search')
        client.waits.forElement(
            id=u'field.actions.search', timeout=constants.FOR_ELEMENT)
        client.click(id=u'field.actions.search')
        client.waits.forElement(
            id=u'filebug-form', timeout=constants.FOR_ELEMENT)

        # No duplicates were found.
        client.asserts.assertText(
            id=u'no-similar-bugs',
            validator=u'No similar bug reports were found.')

        # Check out the expander.
        _test_expander(client)


def _test_expander(client):
    extra_opts_form = u"//fieldset[@id='filebug-extra-options']/div"
    form_closed = u"%s[contains(@class, 'lazr-closed')]" % extra_opts_form
    form_opened = u"%s[contains(@class, 'lazr-opened')]" % extra_opts_form

    # The collapsible area is collapsed and doesn't display.
    client.waits.forElement(xpath=form_closed)

    # Click to expand the extra options form.
    client.click(link=u'Extra options')

    # The collapsible area is expanded and does display.
    client.waits.forElement(xpath=form_opened)
