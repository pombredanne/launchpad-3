# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test subscruber classes and functions."""

__metaclass__ = type

from datetime import datetime

from lazr.lifecycle.event import ObjectModifiedEvent
from lazr.lifecycle.interfaces import IObjectModifiedEvent
import pytz
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.registry.interfaces.person import IPersonViewRestricted
from lp.registry.interfaces.product import License
from lp.registry.subscribers import (
    LicenseNotification,
    person_alteration_security_notice,
    product_licenses_modified,
    )
from lp.services.verification.interfaces.logintoken import ILoginTokenSet
from lp.services.verification.interfaces.authtoken import LoginTokenType
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


class TestPersonDataModifiedHandler(TestCaseWithFactory):
    """When some details of a person change, we need to notify the user."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestPersonDataModifiedHandler, self).setUp()
        self.person = self.factory.makePerson(email='test@pre.com')
        login_person(self.person)
        pop_notifications()

    def check_notification(self):
        notifications = pop_notifications()
        self.assertEqual(1, len(notifications))
        self.assertTrue('test@pre.com' in notifications[0].get('To'))
        self.assertTrue(
            'Preferred email address' in notifications[0].as_string())

    def test_handler_generates_notification(self):
        """Manually firing event generates a proper notification."""
        # After/before objects and list of edited fields.
        event = ObjectModifiedEvent(
            self.person, self.person, ['preferredemail'])
        person_alteration_security_notice(self.person, event)
        self.check_notification()

    def test_event_generates_notification(self):
        """Triggering the event generates a proper notification."""
        new_email = self.factory.makeEmail('test@post.com', self.person)
        self.person.setPreferredEmail(new_email)
        self.check_notification()


class TestPersonAlterationEvent(TestCaseWithFactory):
    """Test that the events are fired when the person is changed."""

    layer = DatabaseFunctionalLayer
    event_listener = None

    def setUp(self):
        super(TestPersonAlterationEvent, self).setUp()
        pop_notifications()
        self.setup_event_listener()
        self.person = self.factory.makePerson(email='test@pre.com')

    def setup_event_listener(self):
        self.events = []
        if self.event_listener is None:
            self.event_listener = TestEventListener(
                IPersonViewRestricted, IObjectModifiedEvent, self.on_event)
        else:
            self.event_listener._active = True
        self.addCleanup(self.event_listener.unregister)

    def check_event(self, edited_field):
        """Verify that the event is the correct one."""
        evt = self.events[0]
        self.assertEqual(self.person, evt.object)
        self.assertEqual('test@pre.com',
            evt.object_before_modification.preferredemail.email)
        self.assertEqual([edited_field], evt.edited_fields)

    def check_notification(self, email_str):
        """Check the actual notification email for correctness."""
        notifications = pop_notifications()
        self.assertTrue('test@pre.com' in notifications[0].get('To'))
        self.assertTrue(email_str in notifications[0].as_string())

    def on_event(self, thing, event):
        self.events.append(event)

    def test_change_preferredemail(self):
        """Event and notification are triggered by preferred email change."""
        new_email = self.factory.makeEmail('test@post.com', self.person)
        with person_logged_in(self.person):
            self.person.setPreferredEmail(new_email)
            self.assertEqual('test@post.com', self.person.preferredemail.email)
            self.assertEqual(1, len(self.events))
            self.check_event('preferredemail')

    def test_no_event_on_no_change(self):
        """No event should be triggered if there's no change."""
        with person_logged_in(self.person):
            self.person.displayname = 'changed'
            self.assertEqual('test@pre.com', self.person.preferredemail.email)
            self.assertEqual(0, len(self.events))

    def test_removed_email_address(self):
        """Event and notification are created when an email is removed."""
        with person_logged_in(self.person):
            secondary_email = self.factory.makeEmail(
                'test@second.com', self.person)
            secondary_email.destroySelf()
            # We should only have one email address, the preferred.
            self.assertEqual('test@pre.com', self.person.preferredemail.email)
            # The preferred email doesn't show in the list of validated emails
            # so there are none left once the destroy is done.
            self.assertEqual(0, self.person.validatedemails.count())
            self.assertEqual(1, len(self.events))
            self.check_event('removedemail')
            self.check_notification('Email address removed')

    def test_new_email_request(self):
        """Event and notification are created when a new email is added."""
        with person_logged_in(self.person):
            secondary_email = self.factory.makeEmail(
                'test@second.com', self.person)
            # The way that a new email address gets requested is through the
            # LoginToken done in the browser/person action_add_email.
            getUtility(ILoginTokenSet).new(self.person,
                self.person.preferredemail.email,
                secondary_email.email,
                LoginTokenType.VALIDATEEMAIL)
            self.assertEqual(1, len(self.events))
            self.check_event('newemail')
            self.check_notification('Email address added')

    def test_new_ssh_key(self):
        """Event and notification are created when users add a ssh key."""
        with person_logged_in(self.person):
            # The factory method generates a fresh ssh key through the
            # SSHKeySet that we're bound into. The view uses the same ssh key
            # set .new method so it's safe to just let the factory trigger our
            # event for us.
            self.factory.makeSSHKey(self.person)
            self.assertEqual(1, len(self.events))
            self.check_event('newsshkey')
            self.check_notification('SSH key added')

    def test_remove_ssh_key(self):
        """Event and notification are created when a user removes a ssh key"""
        with person_logged_in(self.person):
            sshkey = self.factory.makeSSHKey(self.person)
            # Make sure to clear notifications/events before we remove the key.
            pop_notifications()
            self.events = []
            sshkey.destroySelf()
            self.assertEqual(1, len(self.events))
            self.check_event('removedsshkey')
            self.check_notification('SSH key removed')
