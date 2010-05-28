# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test DKIM-signed messages"""

__metaclass__ = type

from email.Message import Message
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.Utils import make_msgid, formatdate
import logging
from textwrap import dedent
import unittest

import dkim

from zope.component import getUtility

from canonical.launchpad.mail import signed_message_from_string
from canonical.launchpad.mail.incoming import (
    authenticateEmail, )
from canonical.launchpad.interfaces.mail import IWeaklyAuthenticatedPrincipal
from lp.registry.interfaces.person import IPersonSet
from lp.testing import TestCaseWithFactory
from canonical.testing.layers import DatabaseFunctionalLayer


# reuse the handler that records log events
from lp.services.sshserver.tests.test_events import ListHandler


class TestSignedMessage(TestCaseWithFactory):
    """Test SignedMessage class correctly extracts and verifies the GPG signatures."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Login with admin roles as we aren't testing access here.
        TestCaseWithFactory.setUp(self, 'admin@canonical.com')
        self._logged_events = []
        handler = ListHandler(self._logged_events)
        logger = logging.getLogger('mail-authenticate-dkim')
        logger.addHandler(handler)
        self.addCleanup(lambda: logger.removeHandler(handler))

    def test_dkim_message_invalid(self):
        # The message message has a syntactically valid DKIM signature that
        # doesn't actually correspond to the sender.  We log something about
        # this but we don't want to drop the message.
        #
        # XXX: This test relies on having real DNS service to look up the
        # signing key.
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
        self.assertTrue(principal.person.preferredemail.email,
            'foo.bar@canonical.com')
        for m in self._logged_events:
            if m.getMessage().find('body hash mismatch') >= 0:
                break
        else:
            self.fail("didn't find message in log")
        # dkim signature here can't be authenticated so we match to the user,
        # but it's weak
        self.assertTrue(
            IWeaklyAuthenticatedPrincipal.providedBy(principal))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
