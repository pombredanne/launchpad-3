# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test subscruber classes and functions."""

__metaclass__ = type

from datetime import datetime

from lazr.lifecycle.event import ObjectModifiedEvent
from lazr.lifecycle.interfaces import IObjectModifiedEvent
import pytz
from zope.security.proxy import removeSecurityProxy

from lp.registry.interfaces.person import IPersonViewRestricted
from lp.registry.interfaces.product import License
from lp.registry.subscribers import (
    LicenseNotification,
    person_details_modified,
    product_licenses_modified,
    )
from lp.services.webapp.publisher import get_current_browser_request
from lp.testing import (
    login_person,
    logout,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.event import TestEventListener
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.mail_helpers import pop_notifications

class ProductLicensesModifiedTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def make_product_event(self, licenses, edited_fields='licenses'):
        product = self.factory.makeProduct(licenses=licenses)
        pop_notifications()
        login_person(product.owner)
        event = ObjectModifiedEvent(
            product, product, edited_fields, user=product.owner)
        return product, event

    def test_product_licenses_modified_licenses_not_edited(self):
        product, event = self.make_product_event(
            [License.OTHER_PROPRIETARY], edited_fields='_owner')
        product_licenses_modified(product, event)
        notifications = pop_notifications()
        self.assertEqual(0, len(notifications))

    def test_product_licenses_modified_licenses_common_license(self):
        product, event = self.make_product_event([License.MIT])
        product_licenses_modified(product, event)
        notifications = pop_notifications()
        self.assertEqual(0, len(notifications))
        request = get_current_browser_request()
        self.assertEqual(0, len(request.response.notifications))

    def test_product_licenses_modified_licenses_other_proprietary(self):
        product, event = self.make_product_event([License.OTHER_PROPRIETARY])
        product_licenses_modified(product, event)
        notifications = pop_notifications()
        self.assertEqual(1, len(notifications))
        request = get_current_browser_request()
        self.assertEqual(1, len(request.response.notifications))

    def test_product_licenses_modified_licenses_other_open_source(self):
        product, event = self.make_product_event([License.OTHER_OPEN_SOURCE])
        product_licenses_modified(product, event)
        notifications = pop_notifications()
        self.assertEqual(1, len(notifications))
        request = get_current_browser_request()
        self.assertEqual(0, len(request.response.notifications))

    def test_product_licenses_modified_licenses_other_dont_know(self):
        product, event = self.make_product_event([License.DONT_KNOW])
        product_licenses_modified(product, event)
        notifications = pop_notifications()
        self.assertEqual(1, len(notifications))
        request = get_current_browser_request()
        self.assertEqual(0, len(request.response.notifications))


class LicenseNotificationTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def make_product_user(self, licenses):
        # Setup an a view that implements ProductLicenseMixin.
        super(LicenseNotificationTestCase, self).setUp()
        user = self.factory.makePerson(
            name='registrant', email='registrant@launchpad.dev')
        login_person(user)
        product = self.factory.makeProduct(
            name='ball', owner=user, licenses=licenses)
        pop_notifications()
        return product, user

    def verify_whiteboard(self, product):
        # Verify that the review whiteboard was updated.
        naked_product = removeSecurityProxy(product)
        entries = naked_product.reviewer_whiteboard.split('\n')
        whiteboard, stamp = entries[-1].rsplit(' ', 1)
        self.assertEqual(
            'User notified of license policy on', whiteboard)

    def verify_user_email(self, notification):
        # Verify that the user was sent an email about the license change.
        self.assertEqual(
            'License information for ball in Launchpad',
            notification['Subject'])
        self.assertEqual(
            'Registrant <registrant@launchpad.dev>',
            notification['To'])
        self.assertEqual(
            'Commercial <commercial@launchpad.net>',
            notification['Reply-To'])

    def test_send_known_license(self):
        # A known license does not generate an email.
        product, user = self.make_product_user([License.GNU_GPL_V2])
        notification = LicenseNotification(product, user)
        result = notification.send()
        self.assertIs(False, result)
        self.assertEqual(0, len(pop_notifications()))

    def test_send_other_dont_know(self):
        # An Other/I don't know license sends one email.
        product, user = self.make_product_user([License.DONT_KNOW])
        notification = LicenseNotification(product, user)
        result = notification.send()
        self.assertIs(True, result)
        self.verify_whiteboard(product)
        notifications = pop_notifications()
        self.assertEqual(1, len(notifications))
        self.verify_user_email(notifications.pop())

    def test_send_other_open_source(self):
        # An Other/Open Source license sends one email.
        product, user = self.make_product_user([License.OTHER_OPEN_SOURCE])
        notification = LicenseNotification(product, user)
        result = notification.send()
        self.assertIs(True, result)
        self.verify_whiteboard(product)
        notifications = pop_notifications()
        self.assertEqual(1, len(notifications))
        self.verify_user_email(notifications.pop())

    def test_send_other_proprietary(self):
        # An Other/Proprietary license sends one email.
        product, user = self.make_product_user([License.OTHER_PROPRIETARY])
        notification = LicenseNotification(product, user)
        result = notification.send()
        self.assertIs(True, result)
        self.verify_whiteboard(product)
        notifications = pop_notifications()
        self.assertEqual(1, len(notifications))
        self.verify_user_email(notifications.pop())

    def test_display_no_request(self):
        # If there is no request, there is no reason to show a message in
        # the browser.
        product, user = self.make_product_user([License.GNU_GPL_V2])
        notification = LicenseNotification(product, user)
        logout()
        result = notification.display()
        self.assertIs(False, result)

    def test_display_no_message(self):
        # A notification is not added if there is no message to show.
        product, user = self.make_product_user([License.GNU_GPL_V2])
        notification = LicenseNotification(product, user)
        result = notification.display()
        self.assertEqual('', notification.getCommercialUseMessage())
        self.assertIs(False, result)

    def test_display_has_message(self):
        # A notification is added if there is a message to show.
        product, user = self.make_product_user([License.OTHER_PROPRIETARY])
        notification = LicenseNotification(product, user)
        result = notification.display()
        message = notification.getCommercialUseMessage()
        self.assertIs(True, result)
        request = get_current_browser_request()
        self.assertEqual(1, len(request.response.notifications))
        self.assertIn(message, request.response.notifications[0].message)
        self.assertIn(
            '<a href="https://help.launchpad.net/CommercialHosting">',
            request.response.notifications[0].message)

    def test_display_escapee_user_data(self):
        # A notification is added if there is a message to show.
        product, user = self.make_product_user([License.OTHER_PROPRIETARY])
        product.displayname = '<b>Look</b>'
        notification = LicenseNotification(product, user)
        result = notification.display()
        self.assertIs(True, result)
        request = get_current_browser_request()
        self.assertEqual(1, len(request.response.notifications))
        self.assertIn(
            '&lt;b&gt;Look&lt;/b&gt;',
            request.response.notifications[0].message)

    def test_formatDate(self):
        # Verify the date format.
        now = datetime(2005, 6, 15, 0, 0, 0, 0, pytz.UTC)
        result = LicenseNotification._formatDate(now)
        self.assertEqual('2005-06-15', result)

    def test_getTemplateName_other_dont_know(self):
        product, user = self.make_product_user([License.DONT_KNOW])
        notification = LicenseNotification(product, user)
        self.assertEqual(
            'product-license-dont-know.txt',
            notification.getTemplateName())

    def test_getTemplateName_propietary(self):
        product, user = self.make_product_user([License.OTHER_PROPRIETARY])
        notification = LicenseNotification(product, user)
        self.assertEqual(
            'product-license-other-proprietary.txt',
            notification.getTemplateName())

    def test_getTemplateName_other_open_source(self):
        product, user = self.make_product_user([License.OTHER_OPEN_SOURCE])
        notification = LicenseNotification(product, user)
        self.assertEqual(
            'product-license-other-open-source.txt',
            notification.getTemplateName())

    def test_getCommercialUseMessage_without_commercial_subscription(self):
        product, user = self.make_product_user([License.MIT])
        notification = LicenseNotification(product, user)
        self.assertEqual('', notification.getCommercialUseMessage())

    def test_getCommercialUseMessage_with_complimentary_cs(self):
        product, user = self.make_product_user([License.OTHER_PROPRIETARY])
        notification = LicenseNotification(product, user)
        message = (
            "Ball's complimentary commercial subscription expires on %s." %
            product.commercial_subscription.date_expires.date().isoformat())
        self.assertEqual(message, notification.getCommercialUseMessage())

    def test_getCommercialUseMessage_with_commercial_subscription(self):
        product, user = self.make_product_user([License.MIT])
        self.factory.makeCommercialSubscription(product)
        product.licenses = [License.MIT, License.OTHER_PROPRIETARY]
        notification = LicenseNotification(product, user)
        message = (
            "Ball's commercial subscription expires on %s." %
            product.commercial_subscription.date_expires.date().isoformat())
        self.assertEqual(message, notification.getCommercialUseMessage())

    def test_getCommercialUseMessage_with_expired_cs(self):
        product, user = self.make_product_user([License.MIT])
        self.factory.makeCommercialSubscription(product, expired=True)
        product.licenses = [License.MIT, License.OTHER_PROPRIETARY]
        notification = LicenseNotification(product, user)
        message = (
            "Ball's commercial subscription expired on %s." %
            product.commercial_subscription.date_expires.date().isoformat())
        self.assertEqual(message, notification.getCommercialUseMessage())
        self.assertEqual(message, notification.getCommercialUseMessage())


class PersonDetailsModifiedTestCase(TestCaseWithFactory):
    """When some details of a person change, we need to notify the user.

    """
    layer = DatabaseFunctionalLayer

    def test_event_generates_notification(self):
        """Manually firing event should generate a proper notification."""
        person = self.factory.makePerson(email='test@pre.com')
        login_person(person)
        pop_notifications()
        # After/before objects and list of edited fields.
        event = ObjectModifiedEvent(person, person, ['preferredemail'])
        person_details_modified(person, event)
        notifications = pop_notifications()
        self.assertEqual(1, len(notifications))
        self.assertTrue('test@pre.com' in notifications[0].get('To'))

    def test_preferred_email_modified(self):
        """Modifying the preferred email should get the notification."""
        person = self.factory.makePerson(email='test@pre.com')
        login_person(person)
        pop_notifications()
        new_email = self.factory.makeEmail('test@post.com', person)
        person.setPreferredEmail(new_email)
        # After/before objects and list of edited fields.
        notifications = pop_notifications()
        self.assertEqual(1, len(notifications))
        self.assertTrue('test@pre.com' in notifications[0].get('To'))


class PersonDetailsModifiedEventTestCase(TestCaseWithFactory):
    """Test that the events are fired when the person is changed."""

    layer = DatabaseFunctionalLayer
    event_listener = None

    def setup_event_listener(self):
        self.events = []
        if self.event_listener is None:
            self.event_listener = TestEventListener(
                IPersonViewRestricted, IObjectModifiedEvent, self.on_event)
        else:
            self.event_listener._active = True
        self.addCleanup(self.event_listener.unregister)

    def on_event(self, thing, event):
        self.events.append(event)

    def test_change_preferredemail(self):
        # The project_reviewed property is not reset, if the new licenses
        # are identical to the current licenses.
        pop_notifications()
        person = self.factory.makePerson(email='test@pre.com')
        new_email = self.factory.makeEmail('test@post.com', person)
        self.setup_event_listener()
        with person_logged_in(person):
            person.setPreferredEmail(new_email)
            # Assert form within the context manager to get access to the
            # email values.
            self.assertEqual('test@post.com', person.preferredemail.email)
            self.assertEqual(1, len(self.events))

            evt = self.events[0]
            self.assertEqual(person, evt.object)
            self.assertEqual('test@pre.com',
                evt.object_before_modification.preferredemail.email)
            self.assertEqual(['preferredemail'], evt.edited_fields)

    def test_no_event_on_no_change(self):
        """If there's no change to the preferred email there's no event"""
        pop_notifications()
        person = self.factory.makePerson(email='test@pre.com')
        self.setup_event_listener()
        with person_logged_in(person):
            person.displayname = 'changed'
            # Assert form within the context manager to get access to the
            # email values.
            self.assertEqual('test@pre.com', person.preferredemail.email)
            self.assertEqual(0, len(self.events))
