# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Tests for the BaseMailer class."""


__metaclass__ = type

from smtplib import SMTPException

from testtools.matchers import EndsWith

from lp.services.mail.basemailer import BaseMailer
from lp.services.mail.sendmail import MailController
from lp.testing import TestCaseWithFactory
from lp.testing.layers import LaunchpadZopelessLayer
from lp.testing.mail_helpers import pop_notifications


class FakeSubscription:
    """Stub for use with these tests."""

    mail_header = 'pete'

    def __init__(self, subscriber):
        self.subscriber = subscriber

    def getReason(self):
        return "Because"


class BaseMailerSubclass(BaseMailer):
    """Subclass of BaseMailer to avoid getting the body template."""

    def _getBody(self, email, recipient):
        return 'body'


class FromAddressUpper(BaseMailerSubclass):
    """Subclass of BaseMailer providing an example getFromAddress."""

    def _getFromAddress(self, email, recipient):
        return self.from_address.upper()


class ToAddressesUpper(BaseMailerSubclass):
    """Subclass of BaseMailer providing an example getToAddresses."""

    def _getToAddresses(self, email, recipient):
        return email.upper()


class AttachmentMailer(BaseMailerSubclass):
    """Subclass the test mailer to add an attachment."""

    def _addAttachments(self, ctrl, email):
        ctrl.addAttachment('attachment1')
        ctrl.addAttachment('attachment2')


class RaisingMailController(MailController):
    """A mail controller that can raise errors."""

    def raiseOnSend(self):
        """Make send fail for the specified email address."""
        self.raise_on_send = True

    def send(self, bulk=True):
        if getattr(self, 'raise_on_send', False):
            raise SMTPException('boom')
        else:
            super(RaisingMailController, self).send(bulk)


class RaisingMailControllerFactory:
    """Pretends to be a class to make raising mail controllers."""

    def __init__(self, bad_email_addr, raise_count):
        self.bad_email_addr = bad_email_addr
        self.raise_count = raise_count

    def __call__(self, *args, **kwargs):
        ctrl = RaisingMailController(*args, **kwargs)
        if ((self.bad_email_addr in kwargs['envelope_to'])
            and self.raise_count):
            self.raise_count -= 1
            ctrl.raiseOnSend()
        return ctrl


class TestBaseMailer(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_generateEmail_sets_envelope_to(self):
        """BaseMailer.generateEmail sets MailController.envelope_to.

        The only item in the list is the supplied email address.
        """
        fake_to = self.factory.makePerson(email='to@example.com',
            displayname='Example To')
        recipients = {fake_to: FakeSubscription(fake_to)}
        mailer = BaseMailerSubclass(
            'subject', None, recipients, 'from@example.com')
        ctrl = mailer.generateEmail('to@example.com', fake_to)
        self.assertEqual(['to@example.com'], ctrl.envelope_to)
        self.assertEqual(['Example To <to@example.com>'], ctrl.to_addrs)

    def test_generateEmail_uses_getFromAddress(self):
        """BaseMailer.generateEmail uses getFromAddress.

        We verify this by using a subclass that provides getFromAddress
        returning the uppercased email address.
        """
        fake_to = self.factory.makePerson(email='to@example.com')
        recipients = {fake_to: FakeSubscription(fake_to)}
        mailer = FromAddressUpper(
            'subject', None, recipients, 'from@example.com')
        ctrl = mailer.generateEmail('to@example.com', fake_to)
        self.assertEqual('FROM@EXAMPLE.COM', ctrl.from_addr)

    def test_generateEmail_uses_getToAddresses(self):
        """BaseMailer.generateEmail uses getToAddresses.

        We verify this by using a subclass that provides getToAddresses
        as a single-item list with the uppercased email address.
        """
        fake_to = self.factory.makePerson(email='to@example.com')
        recipients = {fake_to: FakeSubscription(fake_to)}
        mailer = ToAddressesUpper(
            'subject', None, recipients, 'from@example.com')
        ctrl = mailer.generateEmail('to@example.com', fake_to)
        self.assertEqual(['TO@EXAMPLE.COM'], ctrl.to_addrs)

    def test_generateEmail_adds_attachments(self):
        # BaseMailer.generateEmail calls _addAttachments.
        fake_to = self.factory.makePerson(email='to@example.com')
        recipients = {fake_to: FakeSubscription(fake_to)}
        mailer = AttachmentMailer(
            'subject', None, recipients, 'from@example.com')
        ctrl = mailer.generateEmail('to@example.com', fake_to)
        self.assertEqual(2, len(ctrl.attachments))

    def test_generateEmail_force_no_attachments(self):
        # If BaseMailer.generateEmail is called with
        # force_no_attachments=True then attachments are not added.
        fake_to = self.factory.makePerson(email='to@example.com')
        recipients = {fake_to: FakeSubscription(fake_to)}
        mailer = AttachmentMailer(
            'subject', None, recipients, 'from@example.com')
        ctrl = mailer.generateEmail(
            'to@example.com', fake_to, force_no_attachments=True)
        self.assertEqual(1, len(ctrl.attachments))
        attachment = ctrl.attachments[0]
        self.assertEqual(
            'Excessively large attachments removed.',
            attachment.get_payload())
        self.assertEqual('text/plain', attachment['Content-Type'])
        self.assertEqual('inline', attachment['Content-Disposition'])

    def test_generateEmail_append_no_expanded_footer(self):
        # Recipients without expanded_notification_footers do not receive an
        # expanded footer on messages.
        fake_to = self.factory.makePerson(email='to@example.com')
        recipients = {fake_to: FakeSubscription(fake_to)}
        mailer = BaseMailerSubclass(
            'subject', None, recipients, 'from@example.com',
            notification_type='test')
        ctrl = mailer.generateEmail('to@example.com', fake_to)
        self.assertNotIn('Launchpad-Message-Rationale', ctrl.body)

    def test_generateEmail_append_expanded_footer(self):
        # Recipients with expanded_notification_footers receive an expanded
        # footer on messages.
        fake_to = self.factory.makePerson(
            name='to-person', email='to@example.com')
        fake_to.expanded_notification_footers = True
        recipients = {fake_to: FakeSubscription(fake_to)}
        mailer = BaseMailerSubclass(
            'subject', None, recipients, 'from@example.com',
            notification_type='test')
        ctrl = mailer.generateEmail('to@example.com', fake_to)
        self.assertThat(
            ctrl.body, EndsWith(
                '\n-- \n'
                'Launchpad-Message-Rationale: pete\n'
                'Launchpad-Message-For: to-person\n'
                'Launchpad-Notification-Type: test\n'))

    def test_sendall_single_failure_doesnt_kill_all(self):
        # A failure to send to a particular email address doesn't stop sending
        # to others.
        good = self.factory.makePerson(name='good', email='good@example.com')
        bad = self.factory.makePerson(name='bad', email='bad@example.com')
        recipients = {
            good: FakeSubscription(good),
            bad: FakeSubscription(bad),
            }
        controller_factory = RaisingMailControllerFactory(
            'bad@example.com', 2)
        mailer = BaseMailerSubclass(
            'subject', None, recipients, 'from@example.com',
            mail_controller_class=controller_factory)
        mailer.sendAll()
        # One email is still sent.
        notifications = pop_notifications()
        self.assertEqual(1, len(notifications))
        self.assertEqual('Good <good@example.com>', notifications[0]['To'])
        # And an OOPS is logged.
        self.assertEqual(1, len(self.oopses))
        self.assertIn("SMTPException: boom", self.oopses[0]["tb_text"])

    def test_sendall_first_failure_strips_attachments(self):
        # If sending an email fails, we try again without the (almost
        # certainly) large attachment.
        good = self.factory.makePerson(name='good', email='good@example.com')
        bad = self.factory.makePerson(name='bad', email='bad@example.com')
        recipients = {
            good: FakeSubscription(good),
            bad: FakeSubscription(bad),
            }
        # Only raise the first time for bob.
        controller_factory = RaisingMailControllerFactory(
            'bad@example.com', 1)
        mailer = AttachmentMailer(
            'subject', None, recipients, 'from@example.com',
            mail_controller_class=controller_factory)
        mailer.sendAll()
        # Both emails are sent.
        notifications = pop_notifications()
        self.assertEqual(2, len(notifications))
        bad, good = notifications
        # The good email as the expected attachments.
        good_parts = good.get_payload()
        self.assertEqual(3, len(good_parts))
        self.assertEqual(
            'attachment1', good_parts[1].get_payload(decode=True))
        self.assertEqual(
            'attachment2', good_parts[2].get_payload(decode=True))
        # The bad email has the normal attachments stripped off and replaced
        # with the text.
        bad_parts = bad.get_payload()
        self.assertEqual(2, len(bad_parts))
        self.assertEqual(
            'Excessively large attachments removed.',
            bad_parts[1].get_payload(decode=True))
        # And no OOPS is logged.
        self.assertEqual(0, len(self.oopses))
