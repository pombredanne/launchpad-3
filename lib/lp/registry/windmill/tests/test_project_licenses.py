# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test project licenses picker."""

__metaclass__ = type
__all__ = []

from lp.registry.windmill.testing import RegistryWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill import lpuser
from lp.testing.windmill.constants import PAGE_LOAD


class TestProjectLicenses(WindmillTestCase):
    """Test project licenses picker."""

    layer = RegistryWindmillLayer
    suite_name = 'TestProjectLicenses'

    def test_project_licenses(self):
        """Test the dynamic aspects of the project license picker."""
        # The firefox project is as good as any.
        client, start_url = self.getClientFor(
            '/firefox/+edit', lpuser.SAMPLE_PERSON)

        # The Recommended table is visible.
        client.waits.forElementProperty(
            id=u'recommended',
            option='className|lazr-opened')
        # But the More table is not.
        client.asserts.assertProperty(
            id=u'more',
            validator='className|lazr-closed')
        # Neither is the Other choices.
        client.asserts.assertProperty(
            id=u'special',
            validator='className|lazr-closed')

        # Clicking on the link exposes the More section though.
        client.click(id='more-expand')
        client.waits.forElementProperty(
            id=u'more',
            option='className|lazr-opened')

        # As does clicking on the Other choices section.
        client.click(id='special-expand')
        client.waits.forElementProperty(
            id=u'special',
            option='className|lazr-opened')

        # Clicking on any opened link closes the section.
        client.click(id='recommended-expand')
        client.waits.forElementProperty(
            id=u'recommended',
            option='className|lazr-closed')

        # The license details box starts out hidden.
        client.waits.forElementProperty(
            id=u'license-details',
            option='className|lazr-closed')

        # But clicking on one of the Other/* licenses exposes it.
        client.click(xpath='//input[@value = "OTHER_OPEN_SOURCE"]')
        client.waits.forElementProperty(
            id=u'license-details',
            option='className|lazr-opened')

        # Clicking on Other/Proprietary exposes the additional commercial
        # licensing details.
        client.waits.forElementProperty(
            id=u'proprietary',
            option='className|lazr-closed')

        client.click(xpath='//input[@value = "OTHER_PROPRIETARY"]')
        client.waits.forElementProperty(
            id=u'license-details',
            option='className|lazr-opened')
        client.waits.forElementProperty(
            id=u'proprietary',
            option='className|lazr-opened')

        # Only when all Other/* items are unchecked does the details box get
        # hidden.
        client.click(xpath='//input[@value = "OTHER_OPEN_SOURCE"]')
        client.waits.forElementProperty(
            id=u'license-details',
            option='className|lazr-opened')

        client.click(xpath='//input[@value = "OTHER_PROPRIETARY"]')
        client.waits.forElementProperty(
            id=u'license-details',
            option='className|lazr-closed')
        client.waits.forElementProperty(
            id=u'proprietary',
            option='className|lazr-closed')

        # Clicking on "I haven't specified..." unchecks everything and
        # closes the details box, but leaves the sections opened.

        client.click(xpath='//input[@value = "OTHER_PROPRIETARY"]')
        client.waits.forElementProperty(
            id=u'license-details',
            option='className|lazr-opened')

        client.asserts.assertChecked(
            xpath='//input[@value = "OTHER_PROPRIETARY"]')

        client.click(id='license_pending')
        client.asserts.assertNotChecked(
            xpath='//input[@value = "OTHER_PROPRIETARY"]')

        client.asserts.assertProperty(
            id=u'license-details',
            validator='className|lazr-closed')

        # Submitting the form with items checked ensures that the next
        # time the page is visited, those sections will be open.  The
        # Recommended section is always open.

        client.click(xpath='//input[@value = "OTHER_PROPRIETARY"]')
        client.type(id='field.license_info', text='Foo bar')
        client.click(id='field.licenses.3')
        client.click(id='field.actions.change')
        client.waits.forPageLoad(timeout=PAGE_LOAD)

        client.open(url=u'%s/firefox/+edit'
                        % RegistryWindmillLayer.base_url)
        client.waits.forPageLoad(timeout=PAGE_LOAD)

        client.asserts.assertProperty(
            id=u'more',
            validator='className|lazr-opened')
        # Neither is the Other choices.
        client.asserts.assertProperty(
            id=u'special',
            validator='className|lazr-opened')
        client.asserts.assertProperty(
            id=u'license-details',
            validator='className|lazr-opened')
