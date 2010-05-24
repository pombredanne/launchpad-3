# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

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
from lp.testing import TestCaseWithFactory
from lp.testing.factory import GPGSigningContext
from canonical.testing.layers import DatabaseFunctionalLayer

class TestSignedMessage(TestCaseWithFactory):
    """Test SignedMessage class correctly extracts and verifies the GPG signatures."""

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

    def test_dkim_message_valid(self):
        # The message doesn't have a GPG signature, but it does have a valid
        # DKIM signature.
        #
        # XXX: This test relies on having real DNS service to look up the
        # signing key.
        content = dedent("""\
From martinpool@gmail.com  Fri May 21 06:36:35 2010
Return-Path: <martinpool@gmail.com>
X-Original-To: mbp@ozlabs.org
Delivered-To: mbp@bilbo.ozlabs.org
Received: from mail-pw0-f42.google.com (mail-pw0-f42.google.com [209.85.160.42])
        by ozlabs.org (Postfix) with ESMTP id 176B2B7D2F
        for <mbp@ozlabs.org>; Fri, 21 May 2010 06:36:34 +1000 (EST)
Received: by pwi6 with SMTP id 6so100632pwi.15
        for <mbp@ozlabs.org>; Thu, 20 May 2010 13:36:32 -0700 (PDT)
DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed;
        d=gmail.com; s=gamma;
        h=domainkey-signature:received:mime-version:sender:received:from:date
         :x-google-sender-auth:message-id:subject:to:content-type;
        bh=iTMsDZaf3mTI15MmTPApOkFS873BWrkKZmuxzNgYhxE=;
        b=eV/6q8Tg0fAlbAOktX+R65yCyrUc+qHjXDhvAdo0COLS9p14giPOe/XF3UM58njFXy
         PJhgmL3zSRYBf6z9rrt7FvIKMPJ9RUdaLM+GLxHnkAayrHfe0l8nPGzmAUQWRoQ39OqU
         jUBzOlDJqJZfByQPt0T/FKq40ss5IGNHY4r/k=
DomainKey-Signature: a=rsa-sha1; c=nofws;
        d=gmail.com; s=gamma;
        h=mime-version:sender:from:date:x-google-sender-auth:message-id
         :subject:to:content-type;
        b=vKdO6s1QTFdUNAbhkhQLo44GQiPzWuQoE2P/rmjDO/IIcogl4sAZFjJ/2IQS/e/OTo
         XE/p8DacTe4IXsC2dSHWq+JWFXZrZbYWqq7enwpynifgkqOfHXiYmXQ3sC55UtoRuSRv
         OXqgRsklDFXCiIOMPovuKM39+8pM6gJv26BJE=
Received: by 10.141.91.16 with SMTP id t16mr440375rvl.128.1274387790072; Thu, 
        20 May 2010 13:36:30 -0700 (PDT)
MIME-Version: 1.0
Sender: martinpool@gmail.com
Received: by 10.140.201.21 with HTTP; Thu, 20 May 2010 13:36:10 -0700 (PDT)
From: Martin Pool <mbp@canonical.com>
Date: Fri, 21 May 2010 06:36:10 +1000
X-Google-Sender-Auth: fBmtFoi-TbWWFkOKvHMHqv97pRY
Message-ID: <AANLkTilSBw2H32n8rA7niv3boWbICGgl3bvFdKDNgTe3@mail.gmail.com>
Subject: test
To: mbp@ozlabs.org
Content-Type: text/plain; charset=ISO-8859-1

hello there

-- 
Martin <http://launchpad.net/~mbp/>
""")
        msg = signed_message_from_string(content)
        principal = authenticateEmail(msg)
        self.assertTrue(principal.person.email, 'mbp@canonical.com')
        self.assertFalse(
            IWeaklyAuthenticatedPrincipal.providedBy(principle))

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

