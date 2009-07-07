# Copyright 2009 Canonical Ltd.  All rights reserved.


__metaclass__ = type


import unittest

from canonical.testing import LaunchpadZopelessLayer

from lp.testing import TestCaseWithFactory
from lp.services.mail.basemailer import BaseMailer
from lp.services.mail.notificationrecipientset import NotificationRecipientSet


class FakeSubscription:
    """Stub for use with these tests."""

    mail_header = 'pete'

    def getReason(self):
        return "Because"


class BaseMailerSubclass(BaseMailer):
    """Subclass of BaseMailer to avoid getting the body template."""

    def _getBody(self, email):
        return 'body'


class ToAddressesUpper(BaseMailerSubclass):
    """Subclass of BaseMailer providing an example getToAddresses."""

    def _getToAddresses(self, recipient, email):
        return email.upper()


class TestBaseMailer(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_generateEmail_sets_real_to(self):
        """BaseMailer.generateEmail sets MailController.real_to.

        The only item in the list is the supplied email address.
        """
        fake_to = self.factory.makePerson(email='to@example.com',
            displayname='Example To')
        recipients = {fake_to: FakeSubscription()}
        mailer = BaseMailerSubclass('subject', None, recipients,
                                    'from@example.com')
        ctrl = mailer.generateEmail('to@example.com', fake_to)
        self.assertEqual(['to@example.com'], ctrl.real_to)
        self.assertEqual(['Example To <to@example.com>'], ctrl.to_addrs)

    def test_generateEmail_uses_getToAddresses(self):
        """BaseMailer.generateEmail uses getToAddresses.

        We verify this by using a subclass that provides getToAddresses
        as a single-item list with the uppercased email address.
        """
        fake_to = self.factory.makePerson(email='to@example.com')
        recipients = {fake_to: FakeSubscription()}
        mailer = ToAddressesUpper('subject', None, recipients,
                                  'from@example.com')
        ctrl = mailer.generateEmail('to@example.com', fake_to)
        self.assertEqual(['TO@EXAMPLE.COM'], ctrl.to_addrs)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromName(__name__))
    return suite
