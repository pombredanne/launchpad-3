# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test project licenses picker."""

__metaclass__ = type
__all__ = []

import unittest

from lp.registry.windmill.testing import RegistryWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill import lpuser


class TestProjectLicenses(WindmillTestCase):
    """Test project licenses picker."""

    layer = RegistryWindmillLayer
    suite_name = 'TestProjectLicenses'

    def test_project_licenses(self):
        """Test the dynamic aspects of the project license picker."""
        # The firefox project is as good as any.
        lpuser.SAMPLE_PERSON.ensure_login(self.client)
        self.client.open(url=u'%s/firefox/+edit'
                        % RegistryWindmillLayer.base_url)
        self.client.waits.forPageLoad(timeout=u'20000')

        # The Recommended table is visible.
        self.client.waits.forElementProperty(
            id=u'recommended',
            option='className|lazr-opened')
        # But the More table is not.
        self.client.asserts.assertProperty(
            id=u'more',
            validator='className|lazr-closed')
        # Neither is the Other choices.
        self.client.asserts.assertProperty(
            id=u'special',
            validator='className|lazr-closed')

        # Clicking on the link exposes the More section though.
        self.client.click(id='more-expand')
        self.client.waits.forElementProperty(
            id=u'more',
            option='className|lazr-opened')

        # As does clicking on the Other choices section.
        self.client.click(id='special-expand')
        self.client.waits.forElementProperty(
            id=u'special',
            option='className|lazr-opened')

        # Clicking on any opened link closes the section.
        self.client.click(id='recommended-expand')
        self.client.waits.forElementProperty(
            id=u'recommended',
            option='className|lazr-closed')

        # The license details box starts out hidden.
        self.client.waits.forElementProperty(
            id=u'license-details',
            option='className|lazr-closed')

        # But clicking on one of the Other/* licenses exposes it.
        self.client.click(xpath='//input[@value = "OTHER_OPEN_SOURCE"]')
        self.client.waits.forElementProperty(
            id=u'license-details',
            option='className|lazr-opened')

        # Clicking on Other/Proprietary exposes the additional commercial
        # licensing details.
        self.client.waits.forElementProperty(
            id=u'proprietary',
            option='className|lazr-closed')

        self.client.click(xpath='//input[@value = "OTHER_PROPRIETARY"]')
        self.client.waits.forElementProperty(
            id=u'license-details',
            option='className|lazr-opened')
        self.client.waits.forElementProperty(
            id=u'proprietary',
            option='className|lazr-opened')

        # Only when all Other/* items are unchecked does the details box get
        # hidden.
        self.client.click(xpath='//input[@value = "OTHER_OPEN_SOURCE"]')
        self.client.waits.forElementProperty(
            id=u'license-details',
            option='className|lazr-opened')

        self.client.click(xpath='//input[@value = "OTHER_PROPRIETARY"]')
        self.client.waits.forElementProperty(
            id=u'license-details',
            option='className|lazr-closed')
        self.client.waits.forElementProperty(
            id=u'proprietary',
            option='className|lazr-closed')

        # Clicking on "I haven't specified..." unchecks everything and
        # closes the details box, but leaves the sections opened.

        self.client.click(xpath='//input[@value = "OTHER_PROPRIETARY"]')
        self.client.waits.forElementProperty(
            id=u'license-details',
            option='className|lazr-opened')

        self.client.asserts.assertChecked(
            xpath='//input[@value = "OTHER_PROPRIETARY"]')

        self.client.click(id='license_pending')
        self.client.asserts.assertNotChecked(
            xpath='//input[@value = "OTHER_PROPRIETARY"]')

        self.client.asserts.assertProperty(
            id=u'license-details',
            validator='className|lazr-closed')

        # Submitting the form with items checked ensures that the next
        # time the page is visited, those sections will be open.  The
        # Recommended section is always open.

        self.client.click(xpath='//input[@value = "OTHER_PROPRIETARY"]')
        self.client.type(id='field.license_info', text='Foo bar')
        self.client.click(id='field.licenses.3')
        self.client.click(id='field.actions.change')
        self.client.waits.forPageLoad(timeout=u'20000')

        self.client.open(url=u'%s/firefox/+edit'
                        % RegistryWindmillLayer.base_url)
        self.client.waits.forPageLoad(timeout=u'20000')

        self.client.asserts.assertProperty(
            id=u'more',
            validator='className|lazr-opened')
        # Neither is the Other choices.
        self.client.asserts.assertProperty(
            id=u'special',
            validator='className|lazr-opened')
        self.client.asserts.assertProperty(
            id=u'license-details',
            validator='className|lazr-opened')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
