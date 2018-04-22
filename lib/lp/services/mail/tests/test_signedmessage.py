# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the SignedMessage class."""

__metaclass__ = type

from email.message import Message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import (
    formatdate,
    make_msgid,
    )
from textwrap import dedent

import gpgme
from zope.component import getUtility

from lp.registry.interfaces.person import IPersonSet
from lp.services.gpg.interfaces import IGPGHandler
from lp.services.mail.helpers import IncomingEmailError
from lp.services.mail.incoming import (
    authenticateEmail,
    canonicalise_line_endings,
    )
from lp.services.mail.interfaces import IWeaklyAuthenticatedPrincipal
from lp.services.mail.signedmessage import signed_message_from_string
from lp.testing import TestCaseWithFactory
from lp.testing.factory import GPGSigningContext
from lp.testing.gpgkeys import (
    import_public_test_keys,
    import_secret_test_key,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestSignedMessage(TestCaseWithFactory):
    "Test SignedMessage class correctly extracts and verifies GPG signatures."

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Login with admin roles as we aren't testing access here.
        TestCaseWithFactory.setUp(self, 'admin@canonical.com')
        import_public_test_keys()

    def test_unsigned_message(self):
        # An unsigned message will not have a signature nor signed content,
        # and generates a weakly authenticated principal.
        sender = self.factory.makePerson()
        email_message = self.factory.makeEmailMessage(sender=sender)
        msg = signed_message_from_string(email_message.as_string())
        self.assertIs(None, msg.signedContent)
        self.assertIs(None, msg.signature)
        principal = authenticateEmail(msg)
        self.assertEqual(sender, principal.person)
        self.assertTrue(IWeaklyAuthenticatedPrincipal.providedBy(principal))
        self.assertIs(None, msg.signature)

    def _get_clearsigned_for_person(self, sender, body=None):
        # Create a signed message for the sender specified with the test
        # secret key.
        key = import_secret_test_key()
        signing_context = GPGSigningContext(key, password='test')
        if body is None:
            body = dedent("""\
                This is a multi-line body.

                Sincerely,
                Your friendly tester.
                """)
        msg = self.factory.makeSignedMessage(
            email_address=sender.preferredemail.email,
            body=body, signing_context=signing_context)
        self.assertFalse(msg.is_multipart())
        return signed_message_from_string(msg.as_string())

    def test_clearsigned_message_wrong_sender(self):
        # If the message is signed, but the key doesn't belong to the sender,
        # the principal is set to the sender, but weakly authenticated.
        sender = self.factory.makePerson()
        msg = self._get_clearsigned_for_person(sender)
        principal = authenticateEmail(msg)
        self.assertIsNot(None, msg.signature)
        self.assertEqual(sender, principal.person)
        self.assertTrue(IWeaklyAuthenticatedPrincipal.providedBy(principal))

    def test_clearsigned_message(self):
        # The test keys belong to Sample Person.
        sender = getUtility(IPersonSet).getByEmail('test@canonical.com')
        msg = self._get_clearsigned_for_person(sender)
        principal = authenticateEmail(msg)
        self.assertIsNot(None, msg.signature)
        self.assertEqual(sender, principal.person)
        self.assertFalse(IWeaklyAuthenticatedPrincipal.providedBy(principal))

    def test_trailing_whitespace(self):
        # Trailing whitespace should be ignored when verifying a message's
        # signature.
        sender = getUtility(IPersonSet).getByEmail('test@canonical.com')
        body = (
            'A message with trailing spaces.   \n'
            'And tabs\t\t\n'
            'Also mixed. \t ')
        msg = self._get_clearsigned_for_person(sender, body)
        principal = authenticateEmail(msg)
        self.assertIsNot(None, msg.signature)
        self.assertEqual(sender, principal.person)
        self.assertFalse(IWeaklyAuthenticatedPrincipal.providedBy(principal))

    def _get_detached_message_for_person(self, sender):
        # Return a signed message that contains a detached signature.
        body = dedent("""\
            This is a multi-line body.

            Sincerely,
            Your friendly tester.""")
        to = self.factory.getUniqueEmailAddress()

        msg = MIMEMultipart()
        msg['Message-Id'] = make_msgid('launchpad')
        msg['Date'] = formatdate()
        msg['To'] = to
        msg['From'] = sender.preferredemail.email
        msg['Subject'] = 'Sample'

        body_text = MIMEText(body)
        msg.attach(body_text)
        # A detached signature is calculated on the entire string content of
        # the body message part.
        key = import_secret_test_key()
        gpghandler = getUtility(IGPGHandler)
        signature = gpghandler.signContent(
            canonicalise_line_endings(body_text.as_string()),
            key, 'test', gpgme.SIG_MODE_DETACH)

        attachment = Message()
        attachment.set_payload(signature)
        attachment['Content-Type'] = 'application/pgp-signature'
        msg.attach(attachment)
        self.assertTrue(msg.is_multipart())
        return signed_message_from_string(msg.as_string())

    def test_detached_signature_message_wrong_sender(self):
        # If the message is signed, but the key doesn't belong to the sender,
        # the principal is set to the sender, but weakly authenticated.
        sender = self.factory.makePerson()
        msg = self._get_detached_message_for_person(sender)
        principal = authenticateEmail(msg)
        self.assertIsNot(None, msg.signature)
        self.assertEqual(sender, principal.person)
        self.assertTrue(IWeaklyAuthenticatedPrincipal.providedBy(principal))

    def test_detached_signature_message(self):
        # Test a detached correct signature.
        sender = getUtility(IPersonSet).getByEmail('test@canonical.com')
        msg = self._get_detached_message_for_person(sender)
        principal = authenticateEmail(msg)
        self.assertIsNot(None, msg.signature)
        self.assertEqual(sender, principal.person)
        self.assertFalse(IWeaklyAuthenticatedPrincipal.providedBy(principal))

    def test_require_strong_email_authentication_and_signed(self):
        sender = getUtility(IPersonSet).getByEmail('test@canonical.com')
        sender.require_strong_email_authentication = True
        msg = self._get_clearsigned_for_person(sender)
        principal = authenticateEmail(msg)
        self.assertIsNot(None, msg.signature)
        self.assertEqual(sender, principal.person)
        self.assertFalse(IWeaklyAuthenticatedPrincipal.providedBy(principal))

    def test_require_strong_email_authentication_and_unsigned(self):
        sender = getUtility(IPersonSet).getByEmail('test@canonical.com')
        sender.require_strong_email_authentication = True
        email_message = self.factory.makeEmailMessage(sender=sender)
        msg = signed_message_from_string(email_message.as_string())
        error = self.assertRaises(IncomingEmailError, authenticateEmail, msg)
        expected_message = (
            "Launchpad only accepts signed email from your address.\n\n"
            "If you want to use the Launchpad email interface, you will need "
            "to go here\n"
            "to import your OpenPGP key and then use it to sign your "
            "messages:\n\n"
            "  http://launchpad.dev/~%s/+editpgpkeys\n\n"
            "If you did not knowingly send email to Launchpad, then spammers "
            "may be\n"
            "forging messages as if they were sent from your address, perhaps "
            "due to\n"
            "a compromised address book, and you can safely ignore this "
            "message.\n" % sender.name)
        self.assertEqual(expected_message, error.message)
