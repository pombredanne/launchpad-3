# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for using a person picker widget."""

__metaclass__ = type
__all__ = []

import unittest

from lp.registry.windmill.testing import RegistryWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill import (
    constants,
    lpuser,
    )


VISIBLE_PICKER_OVERLAY = (
    u'//div[contains(@class, "yui3-picker ") and '
     'not(contains(@class, "yui3-picker-hidden"))]')


class TesPersonPickerWidget(WindmillTestCase):

    layer = RegistryWindmillLayer
    suite_name = 'PersonPickerWidget'

    def test_person_picker_widget(self):
        client = self.client
        lpuser.SAMPLE_PERSON.ensure_login(client)

        client.open(url=u'%s/people/+requestmerge'
                    % RegistryWindmillLayer.base_url)
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        client.waits.forElement(id=u'show-widget-field-dupe_person',
                                timeout=constants.FOR_ELEMENT)

        client.type(text=u'guilherme', name=u'field.dupe_person')

        client.click(id=u'show-widget-field-dupe_person')
        client.waits.forElement(xpath=VISIBLE_PICKER_OVERLAY,
                                timeout=constants.FOR_ELEMENT)

        client.asserts.assertProperty(
            xpath=u'//div[@class="yui3-picker-search-box"]/input',
            validator=u'value|guilherme')

        client.click(xpath=u'//div[@class="yui3-picker-search-box"]/button')
        client.waits.sleep(milliseconds=constants.SLEEP)

        client.click(xpath=u'//ul[@class="yui3-picker-results"]/li[1]')
        client.asserts.assertProperty(
            xpath=u'//input[@name="field.dupe_person"]',
            validator='value|salgado')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
