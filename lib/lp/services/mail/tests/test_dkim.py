# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test DKIM-signed messages"""

__metaclass__ = type

from email.Message import Message
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.Utils import make_msgid, formatdate
from textwrap import dedent
import unittest

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

    def test_dkim_message_valid(self):
        # The message doesn't have a GPG signature, but it does have a valid
        # DKIM signature.
        #
        # XXX: This test relies on having real DNS service to look up the
        # signing key.
        #
        # Must match a user declared in the sample data
        content = dedent("""\
From foo.bar@canonical.com  Fri May 21 06:36:35 2010
DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed;
        d=gmail.com; s=gamma;
        h=domainkey-signature:received:mime-version:sender:received:from:date
         :x-google-sender-auth:message-id:subject:to:content-type;
        bh=iTMsDZaf3mTI15MmTPApOkFS873BWrkKZmuxzNgYhxE=;
        b=eV/6q8Tg0fAlbAOktX+R65yCyrUc+qHjXDhvAdo0COLS9p14giPOe/XF3UM58njFXy
         PJhgmL3zSRYBf6z9rrt7FvIKMPJ9RUdaLM+GLxHnkAayrHfe0l8nPGzmAUQWRoQ39OqU
         jUBzOlDJqJZfByQPt0T/FKq40ss5IGNHY4r/k=
MIME-Version: 1.0
Sender: foo.bar@canonical.com
From: Foo Bar <foo.bar@canonical.com>
Date: Fri, 21 May 2010 06:36:10 +1000
Message-ID: <123123123@example.canonical.com>
Subject: dkim sample
To: 1@bugs.launchpad.dev
Content-Type: text/plain; charset=ISO-8859-1

hello there

-- 
Foo Bar
""")
        msg = signed_message_from_string(content)
        principal = authenticateEmail(msg)
        self.assertTrue(principal.person.email, 'foo.bar@canonical.com')
        self.assertFalse(
            IWeaklyAuthenticatedPrincipal.providedBy(principle))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
