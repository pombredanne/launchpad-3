# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test for using a DateTime Calendar widget."""

__metaclass__ = type
__all__ = []

from canonical.launchpad.windmill.testing import lpuser

from windmill.authoring import WindmillTestClient

def test_datetime_calendar_widget():
    """Test the calendar widget's general functionality.

    This test ensures that, with Javascript enabled, an input field
    with the 'yui-calendar' class will get an extra 'choose...' link
    which opens up a calendar widget. The extra class 'withtime' is
    used to optionally include time fields.
    """
    client = WindmillTestClient("Datetime calendar widget test")
    lpuser.SAMPLE_PERSON.ensure_login(client)

    # Open a new sprint page and wait for it to finish loading.
    client.open(url=u'http://blueprints.launchpad.dev:8085/sprints/+new')
    client.waits.forPageLoad(timeout=u'20000')
    client.waits.forElement(link=u'Choose...', timeout=u'8000')

    # Enter a date directly in the field first (which will ensure
    # the calendar widget opens with this date.)
    client.click(id=u'field.time_starts')
    client.type(text=u'2009-05-08 10:04', id=u'field.time_starts')

    # Open the calendar widget
    client.click(link=u'Choose...')

    # Initially choose the 21st of May 2009 and verify that the input
    # field's value has changed.
    client.click(link=u'21')
    client.asserts.assertValue(validator=u'2009-05-21 10:04',
                               id=u'field.time_starts')

    # Navigate to the next month, select the 9th, enter a time of 10:30
    # and click the close/confirm button, then verify the correct value
    # is in the field.
    client.click(link=u'Next Month (June 2009)')
    client.click(link=u'9')
    client.type(
        xpath=(u"//div[@id='calendar_container-field.time_starts']"
               u"/div[2]/input"),
        text=u'10')

    client.type(
        xpath=(u"//div[@id='calendar_container-field.time_starts']"
               u"/div[2]/input[2]"),
        text=u'30')

    client.click(xpath=(u"//div[@id='calendar_container-field.time_starts']"
                        u"/div[2]/button"))
    client.asserts.assertValue(validator=u'2009-06-09 10:30',
                               id=u'field.time_starts')

