# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from doctest import DocTestSuite
import email
import time
import unittest

from zope.component import getUtility

from canonical.database.sqlbase import commit
from canonical.launchpad.interfaces.gpghandler import IGPGHandler
from canonical.launchpad.ftests import import_secret_test_key
from canonical.launchpad.mail.commands import BugEmailCommand
from canonical.launchpad.mail.handlers import MaloneHandler
from canonical.launchpad.mail.incoming import canonicalise_line_endings
from canonical.testing import LaunchpadFunctionalLayer
from lp.services.mail import stub
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.factory import GPGSigningContext


class TestMaloneHandler(TestCaseWithFactory):
    """Test that the Malone/bugs handler works."""

    layer = LaunchpadFunctionalLayer

    def test_getCommandsEmpty(self):
        """getCommands returns an empty list for messages with no command."""
        message = self.factory.makeSignedMessage()
        handler = MaloneHandler()
        self.assertEqual([], handler.getCommands(message))

    def test_getCommandsBug(self):
        """getCommands returns a reasonable list if commands are specified."""
        message = self.factory.makeSignedMessage(body=' bug foo')
        handler = MaloneHandler()
        commands = handler.getCommands(message)
        self.assertEqual(1, len(commands))
        self.assertTrue(isinstance(commands[0], BugEmailCommand))
        self.assertEqual('bug', commands[0].name)
        self.assertEqual(['foo'], commands[0].string_args)


class FakeSignature:

    def __init__(self, timestamp):
        self.timestamp = timestamp


def get_last_email():
    from_addr, to_addrs, raw_message = stub.test_emails[-1]
    sent_msg = email.message_from_string(raw_message)
    error_mail, original_mail = sent_msg.get_payload()
    # clear the emails so we don't accidentally get one from a previous test
    return dict(
        subject=sent_msg['Subject'],
        body=error_mail.get_payload(decode=True))


BAD_SIGNATURE_TIMESTAMP_MESSAGE = (
    'The message you sent included commands to modify the bug '
    'report, but the\nsignature was (apparently) generated too far '
    'in the past or future.')


class TestSignatureTimestampValidation(TestCaseWithFactory):
    """GPG signature timestamps are checked for emails containing commands."""

    layer = LaunchpadFunctionalLayer

    def test_good_signature_timestamp(self):
        # An email message's GPG signature's timestamp checked to be sure it
        # isn't too far in the future or past.  This test shows that a
        # signature with a timestamp of appxoimately now will be accepted.
        signing_context = GPGSigningContext(
            import_secret_test_key().fingerprint, password='test')
        msg = self.factory.makeSignedMessage(
            body=' security no', signing_context=signing_context)
        handler = MaloneHandler()
        with person_logged_in(self.factory.makePerson()):
            success = handler.process(msg, msg['To'])
        commit()
        # Since there were no commands in the poorly-timestamped message, no
        # error emails were generated.
        self.assertEqual(stub.test_emails, [])

    def test_bad_timestamp_but_no_commands(self):
        # If an email message's GPG signature's timestamp is too far in the
        # future or past but it doesn't contain any commands, the email is
        # processed anyway.

        msg = self.factory.makeSignedMessage(
            body='I really hope this bug gets fixed.')
        now = time.time()
        one_week = 60 * 60 * 24 * 7
        msg.signature = FakeSignature(timestamp=now+one_week)
        handler = MaloneHandler()
        # Clear old emails before potentially generating more.
        del stub.test_emails[:]
        with person_logged_in(self.factory.makePerson()):
            success = handler.process(msg, msg['To'])
        commit()
        # Since there were no commands in the poorly-timestamped message, no
        # error emails were generated.
        self.assertEqual(stub.test_emails, [])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests(DocTestSuite('canonical.launchpad.mail.handlers'))
    suite.addTests(unittest.TestLoader().loadTestsFromName(__name__))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
