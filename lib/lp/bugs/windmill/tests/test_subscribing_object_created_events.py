# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import unittest

from canonical.launchpad.ftests.event import TestEventListener
from canonical.launchpad.windmill.testing import lpuser
from canonical.launchpad.windmill.testing.constants import (
    PAGE_LOAD, FOR_ELEMENT, SLEEP)
from lazr.lifecycle.event import IObjectCreatedEvent
from lp.bugs.interfaces.bugsubscription import IBugSubscription
from lp.bugs.windmill.testing import BugsWindmillLayer
from lp.services.mail import stub
from lp.testing import WindmillTestCase


class TestSubscribingObjectCreatedEvents(WindmillTestCase):

    layer = BugsWindmillLayer
    suite_name = 'ObjectCreatedEvent from subscribing test'
    collected_events = []

    def setUpEventListeners(self):
        """Install a listener for events emitted during the test."""
        self.created_event_listener = TestEventListener(
            IBugSubscription, IObjectCreatedEvent, self.collectEvent)

    def collectEvent(self, object, event):
        self.collected_events.append(event)

    def test_object_created_event_from_subscribing(self):

        client = self.client
        self.setUpEventListeners()

        # Confirm no ObjectCreatedEvents exist yet.
        self.assertEqual(len(self.collected_events), 0)

        # Subscribe to bug #11.
        client.open(url='http://bugs.launchpad.dev:8085/bugs/11')
        client.waits.forPageLoad(timeout=PAGE_LOAD)
        lpuser.SAMPLE_PERSON.ensure_login(client)
        client.waits.forElement(id=u'subscribers-links', timeout=FOR_ELEMENT)
        client.click(link='Subscribe')
        client.waits.forElement(link='Unsubscribe', timeout=FOR_ELEMENT)

        self.assertEqual(len(self.collected_events), 1)

        # Subscribe someone else to the bug.
        client.click(link=u'Subscribe someone else')
        client.waits.forElement(
            name=u'search', timeout=FOR_ELEMENT)
        client.type(text=u'mark', name=u'search')
        client.click(
            xpath=u'//table[contains(@class, "yui-picker") '
                   'and not(contains(@class, "yui-picker-hidden"))]'
                   '//div[@class="yui-picker-search-box"]/button')
        search_result_xpath = (
            u'//table[contains(@class, "yui-picker") '
            'and not(contains(@class, "yui-picker-hidden"))]'
            '//ul[@class="yui-picker-results"]/li[1]/span')
        # sleep() seems to be the only way to get this section to pass
        # when running all of BugsWindmillLayer.
        client.waits.sleep(milliseconds=SLEEP)
        client.click(xpath=search_result_xpath)
        person_xpath  = u'//div[@id="subscribers-links"]/div/a[@name="%s"]'
        client.waits.forElement(
            xpath=person_xpath % u'Mark Shuttleworth', timeout=FOR_ELEMENT)

        self.assertEqual(len(self.collected_events), 2)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
