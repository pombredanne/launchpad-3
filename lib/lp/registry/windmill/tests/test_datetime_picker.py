# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for using a DateTime Calendar widget."""

__metaclass__ = type
__all__ = []

import unittest

from canonical.launchpad.windmill.testing import lpuser
from lp.registry.windmill.testing import RegistryWindmillLayer
from lp.testing import WindmillTestCase


class TestDateTimeCalendarWidget(WindmillTestCase):
    """Test datetime calendar widget."""

    layer = RegistryWindmillLayer
    suite_name = 'DateTimeCalendarWidget'

    def test_datetime_calendar_widget(self):
        """Test the calendar widget's general functionality.

        This test ensures that, with Javascript enabled, an input field
        with the 'yui3-calendar' class will get an extra 'choose...' link
        which opens up a calendar widget. The extra class 'withtime' is
        used to optionally include time fields.
        """
        lpuser.SAMPLE_PERSON.ensure_login(self.client)

        # Open a new sprint page and wait for it to finish loading.
        self.client.open(
            url=u'%s/sprints/+new'
                % self.layer.appserver_root_url('blueprints'))
        self.client.waits.forPageLoad(timeout=u'20000')
        self.client.waits.forElement(link=u'Choose...', timeout=u'8000')

        # Enter a date directly in the field first (which will ensure
        # the calendar widget opens with this date.)
        self.client.click(id=u'field.time_starts')
        self.client.type(text=u'2009-05-08 10:04', id=u'field.time_starts')

        # Open the calendar widget
        self.client.click(link=u'Choose...')

        # Initially choose the 21st of May 2009 and verify that the input
        # field's value has changed.
        self.client.click(link=u'21')
        self.client.asserts.assertValue(
            validator=u'2009-05-21 10:04', id=u'field.time_starts')

        # Navigate to the next month, select the 9th, enter a time of 10:30
        # and click the close/confirm button, then verify the correct value
        # is in the field.
        self.client.click(link=u'Next Month (June 2009)')
        self.client.click(link=u'9')
        self.client.type(
            xpath=(u"//div[@id='calendar_container-field.time_starts']"
                   u"/div[2]/input"),
            text=u'10')

        self.client.type(
            xpath=(u"//div[@id='calendar_container-field.time_starts']"
                   u"/div[2]/input[2]"),
            text=u'30')

        self.client.click(
            xpath=(u"//div[@id='calendar_container-field.time_starts']"
                   u"/div[2]/button"))
        self.client.asserts.assertValue(
            validator=u'2009-06-09 10:30', id=u'field.time_starts')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
