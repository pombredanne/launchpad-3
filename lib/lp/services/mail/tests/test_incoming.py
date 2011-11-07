# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from doctest import DocTestSuite
import logging
import os
import unittest

from testtools.matchers import (
    Equals,
    Is,
    )
import transaction
from zope.security.management import setSecurityPolicy

from canonical.config import config
from canonical.launchpad.ftests import import_secret_test_key
from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite
from canonical.launchpad.webapp.authorization import LaunchpadSecurityPolicy
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.services.log.logger import BufferLogger
from lp.services.mail import helpers
from lp.services.mail.incoming import (
    authenticateEmail,
    extract_addresses,
    handleMail,
    ORIGINAL_TO_HEADER,
    )
from lp.services.mail.sendmail import MailController
from lp.services.mail.stub import TestMailer
from lp.services.mail.tests.helpers import testmails_path
from lp.testing import TestCaseWithFactory
from lp.testing.factory import GPGSigningContext
from lp.testing.mail_helpers import pop_notifications


class TestIncoming(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_invalid_signature(self):
        """Invalid signature should not be handled as an OOPs.

        It should produce a message explaining to the user what went wrong.
        """
        person = self.factory.makePerson()
        transaction.commit()
        email_address = person.preferredemail.email
        invalid_body = (
            '-----BEGIN PGP SIGNED MESSAGE-----\n'
            'Hash: SHA1\n\n'
            'Body\n'
            '-----BEGIN PGP SIGNATURE-----\n'
            'Not a signature.\n'
            '-----END PGP SIGNATURE-----\n')
        ctrl = MailController(
            email_address, 'to@example.com', 'subject', invalid_body,
            bulk=False)
        ctrl.send()
        handleMail()
        self.assertEqual([], self.oopses)
        [notification] = pop_notifications()
        body = notification.get_payload()[0].get_payload(decode=True)
        self.assertIn(
            "An error occurred while processing a mail you sent to "
            "Launchpad's email\ninterface.\n\n\n"
            "Error message:\n\nSignature couldn't be verified: No data",
            body)

    def test_invalid_to_addresses(self):
        """Invalid To: header should not be handled as an OOPS."""
        raw_mail = open(os.path.join(
            testmails_path, 'invalid-to-header.txt')).read()
        # Due to the way handleMail works, even if we pass a valid To header
        # to the TestMailer, as we're doing here, it falls back to parse all
        # To and CC headers from the raw_mail. Also, TestMailer is used here
        # because MailController won't send an email with a broken To: header.
        TestMailer().send("from@example.com", "to@example.com", raw_mail)
        handleMail()
        self.assertEqual([], self.oopses)

    def test_bad_signature_timestamp(self):
        """If the signature is nontrivial future-dated, it's not trusted."""

        signing_context = GPGSigningContext(
            import_secret_test_key().fingerprint, password='test')
        msg = self.factory.makeSignedMessage(signing_context=signing_context)
        # It's not trivial to make a gpg signature with a bogus timestamp, so
        # let's just treat everything as invalid, and trust that the regular
        # implementation of extraction and checking of timestamps is correct,
        # or at least tested.

        def fail_all_timestamps(timestamp, context):
            raise helpers.IncomingEmailError("fail!")
        self.assertRaises(
            helpers.IncomingEmailError,
            authenticateEmail,
            msg, fail_all_timestamps)

    def test_unknown_email(self):
        # An unknown email address returns no principal.
        unknown = 'random-unknown@example.com'
        mail = self.factory.makeSignedMessage(email_address=unknown)
        self.assertThat(authenticateEmail(mail), Is(None))

    def test_accounts_without_person(self):
        # An account without a person should be the same as an unknown email.
        email = 'non-person@example.com'
        self.factory.makeAccount(email=email)
        mail = self.factory.makeSignedMessage(email_address=email)
        self.assertThat(authenticateEmail(mail), Is(None))


class TestExtractAddresses(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_original_to(self):
        mail = self.factory.makeSignedMessage()
        original_to = 'eric@vikings.example.com'
        mail[ORIGINAL_TO_HEADER] = original_to
        self.assertThat(
            extract_addresses(mail, None, None),
            Equals([original_to]))

    def test_original_to_in_body(self):
        header_to = 'eric@vikings-r-us.example.com'
        original_to = 'eric@vikings.example.com'
        alias = 'librarian-somewhere'
        body = '%s: %s\n\nsome body stuff' % (
            ORIGINAL_TO_HEADER, original_to)
        log = BufferLogger()
        mail = self.factory.makeSignedMessage(
            body=body, to_address=header_to)
        addresses = extract_addresses(mail, alias, log)
        self.assertThat(addresses, Equals([header_to]))
        self.assertThat(
            log.getLogBuffer(),
            Equals('INFO Suspected spam: librarian-somewhere\n'))

    def test_original_to_missing(self):
        header_to = 'eric@vikings-r-us.example.com'
        alias = 'librarian-somewhere'
        log = BufferLogger()
        mail = self.factory.makeSignedMessage(to_address=header_to)
        addresses = extract_addresses(mail, alias, log)
        self.assertThat(addresses, Equals([header_to]))
        self.assertThat(
            log.getLogBuffer(),
            Equals('WARNING No X-Launchpad-Original-To header was present '
                   'in email: librarian-somewhere\n'))


def setUp(test):
    test._old_policy = setSecurityPolicy(LaunchpadSecurityPolicy)
    LaunchpadZopelessLayer.switchDbUser(config.processmail.dbuser)


def tearDown(test):
    setSecurityPolicy(test._old_policy)


def test_suite():
    suite = unittest.TestLoader().loadTestsFromName(__name__)
    suite.addTest(DocTestSuite('lp.services.mail.incoming'))
    suite.addTest(
        LayeredDocFileSuite(
            'incomingmail.txt',
            setUp=setUp,
            tearDown=tearDown,
            layer=LaunchpadZopelessLayer,
            stdout_logging_level=logging.WARNING))
    return suite
