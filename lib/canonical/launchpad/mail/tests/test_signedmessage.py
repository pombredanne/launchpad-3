# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test the SignedMessage class."""

__metaclass__ = type

from email.Message import Message
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.Utils import make_msgid, formatdate
from textwrap import dedent
import unittest

import gpgme
from zope.component import getUtility

from canonical.launchpad.mail import signed_message_from_string
from canonical.launchpad.mail.incoming import (
    authenticateEmail, canonicalise_line_endings)
from canonical.launchpad.ftests import (
    import_public_test_keys, import_secret_test_key)
from canonical.launchpad.interfaces.gpghandler import IGPGHandler
from canonical.launchpad.interfaces.mail import IWeaklyAuthenticatedPrincipal
from lp.registry.interfaces.person import IPersonSet
from canonical.launchpad.testing import GPGSigningContext, TestCaseWithFactory
from canonical.testing.layers import DatabaseFunctionalLayer

class TestSignedMessage(TestCaseWithFactory):
    """Test SignedMessage class correctly extracts the GPG signatures."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Login with admin roles as we aren't testing access here.
        TestCaseWithFactory.setUp(self, 'admin@canonical.com')
        import_public_test_keys()

    def test_unsigned_message(self):
        # An unsigned message will not have a signature nor signed content,
        # and generates a weakly authenticated principle.
        sender = self.factory.makePerson()
        email_message = self.factory.makeEmailMessage(sender=sender)
        msg = signed_message_from_string(email_message.as_string())
        self.assertIs(None, msg.signedContent)
        self.assertIs(None, msg.signature)
        principle = authenticateEmail(msg)
        self.assertEqual(sender, principle.person)
        self.assertTrue(
            IWeaklyAuthenticatedPrincipal.providedBy(principle))
        self.assertIs(None, msg.signature)

    def _get_clearsigned_for_person(self, sender):
        # Create a signed message for the sender specified with the test
        # secret key.
        key = import_secret_test_key()
        signing_context = GPGSigningContext(key.fingerprint, password='test')
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
        # the principle is set to the sender, but weakly authenticated.
        sender = self.factory.makePerson()
        msg = self._get_clearsigned_for_person(sender)
        principle = authenticateEmail(msg)
        self.assertIsNot(None, msg.signature)
        self.assertEqual(sender, principle.person)
        self.assertTrue(
            IWeaklyAuthenticatedPrincipal.providedBy(principle))

    def test_clearsigned_message(self):
        # The test keys belong to Sample Person.
        sender = getUtility(IPersonSet).getByEmail('test@canonical.com')
        msg = self._get_clearsigned_for_person(sender)
        principle = authenticateEmail(msg)
        self.assertIsNot(None, msg.signature)
        self.assertEqual(sender, principle.person)
        self.assertFalse(
            IWeaklyAuthenticatedPrincipal.providedBy(principle))

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
            key.fingerprint, 'test', gpgme.SIG_MODE_DETACH)

        attachment = Message()
        attachment.set_payload(signature)
        attachment['Content-Type'] = 'application/pgp-signature'
        msg.attach(attachment)
        self.assertTrue(msg.is_multipart())
        return signed_message_from_string(msg.as_string())

    def test_detached_signature_message_wrong_sender(self):
        # If the message is signed, but the key doesn't belong to the sender,
        # the principle is set to the sender, but weakly authenticated.
        sender = self.factory.makePerson()
        msg = self._get_detached_message_for_person(sender)
        principle = authenticateEmail(msg)
        self.assertIsNot(None, msg.signature)
        self.assertEqual(sender, principle.person)
        self.assertTrue(
            IWeaklyAuthenticatedPrincipal.providedBy(principle))

    def test_detached_signature_message(self):
        # Test a detached correct signature.
        sender = getUtility(IPersonSet).getByEmail('test@canonical.com')
        msg = self._get_detached_message_for_person(sender)
        principle = authenticateEmail(msg)
        self.assertIsNot(None, msg.signature)
        self.assertEqual(sender, principle.person)
        self.assertFalse(
            IWeaklyAuthenticatedPrincipal.providedBy(principle))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

