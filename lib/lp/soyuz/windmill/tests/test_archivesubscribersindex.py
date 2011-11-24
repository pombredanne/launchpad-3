# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for the archive subscribers index page.."""

__metaclass__ = type
__all__ = []

import transaction
from zope.component import getUtility

from lp.registry.interfaces.distribution import IDistributionSet
from lp.soyuz.windmill.testing import SoyuzWindmillLayer
from lp.testing import (
    login,
    logout,
    WindmillTestCase,
    )
from lp.testing.windmill import constants
from lp.testing.windmill.lpuser import LaunchpadUser


ADD_ACCESS_LINK = u'//a[@class="js-action sprite add"]'
CHOOSE_SUBSCRIBER_LINK = u'//a[@id="show-widget-field-subscriber"]'
SUBSCRIBER_SEARCH_FIELD = (
    u'//div[@id="yui3-pretty-overlay-modal"]//input[@name="search"]')
SUBSCRIBER_SEARCH_BUTTON = u'//div[@id="yui3-pretty-overlay-modal"]//button'
FIRST_SUBSCRIBER_RESULT = (
    u'//div[@id="yui3-pretty-overlay-modal"]'
     '//span[@class="yui3-picker-result-title"]')
MESSAGE_WINDOW = u'//div[@class="informational message"]'


class TestArchiveSubscribersIndex(WindmillTestCase):

    layer = SoyuzWindmillLayer
    suite_name = 'Adding private PPA subscribers.'

    def setUp(self):
        """Create a private PPA."""
        super(TestArchiveSubscribersIndex, self).setUp()

        user = self.factory.makePerson(
            name='joe-bloggs', email='joe@example.com', password='joe',
            displayname='Joe Bloggs')
        ubuntu = getUtility(IDistributionSet)['ubuntu']
        self.ppa = self.factory.makeArchive(
            owner=user, name='myppa', distribution=ubuntu)

        login('foo.bar@canonical.com')
        self.ppa.private = True
        self.ppa.buildd_secret = 'secret'
        logout()
        transaction.commit()

        self.lpuser = LaunchpadUser(
            'Joe Bloggs', 'joe@example.com', 'joe')

    def test_add_subscriber(self):
        """Test adding a private PPA subscriber.."""

        client, start_url = self.getClientFor(
            '/~joe-bloggs/+archive/myppa/+subscriptions', self.lpuser)

        # Click on the JS add access action.
        client.waits.forElement(
            xpath=ADD_ACCESS_LINK, timeout=constants.FOR_ELEMENT)
        client.click(xpath=ADD_ACCESS_LINK)

        # Open the picker, search for 'launchpad' and choose the first
        # result
        client.click(xpath=CHOOSE_SUBSCRIBER_LINK)
        client.type(xpath=SUBSCRIBER_SEARCH_FIELD, text='launchpad')
        client.click(xpath=SUBSCRIBER_SEARCH_BUTTON)

        client.waits.forElement(
            xpath=FIRST_SUBSCRIBER_RESULT, timeout=constants.FOR_ELEMENT)
        client.click(xpath=FIRST_SUBSCRIBER_RESULT)

        # Add the new subscriber.
        client.click(id='field.actions.add')
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)

        # And verify that the correct informational message is displayed.
        # It would be nice if we could use ... here.
        client.waits.forElement(
            xpath=MESSAGE_WINDOW, timeout=constants.FOR_ELEMENT)
        client.asserts.assertText(
            xpath=u'//div[@class="informational message"]',
            validator='You have granted access for Launchpad Developers '
                      'to install software from PPA named myppa for Joe '
                      'Bloggs. Members of Launchpad Developers will be '
                      'notified of the access  via email.')
