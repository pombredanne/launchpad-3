# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test MaloneHandler."""

__metaclass__ = type

import email
import time

import transaction

from canonical.config import config
from canonical.database.sqlbase import commit
from canonical.launchpad.ftests import import_secret_test_key
from canonical.launchpad.mail.commands import BugEmailCommand
from canonical.testing.layers import (
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    ZopelessAppServerLayer,
    )
from lp.bugs.mail.handler import MaloneHandler
from lp.services.mail import stub
from lp.testing import (
    login,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.factory import GPGSigningContext
from lp.testing.mail_helpers import pop_notifications


class TestMaloneHandler(TestCaseWithFactory):
    """Test that the Malone/bugs handler works."""

    layer = ZopelessAppServerLayer

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

    def test_NonGPGAuthenticatedNewBug(self):
        """Mail authenticated other than by gpg can create bugs.

        The incoming mail layer is responsible for authenticating the mail,
        and setting the current principal to the sender of the mail, either
        weakly or non-weakly authenticated.  At the layer of the handler,
        which this class is testing, we shouldn't care by what mechanism we
        decided to act on behalf of the mail sender, only that we did.

        In bug 643219, Launchpad had a problem where the MaloneHandler code
        was puncturing that abstraction and directly looking at the GPG
        signature; this test checks it's fixed.
        """
        # NB SignedMessage by default isn't actually signed, it just has the
        # capability of knowing about signing.
        message = self.factory.makeSignedMessage(body='  affects malone\nhi!')
        self.assertEquals(message.signature, None)

        # Pretend that the mail auth has given us a logged-in user.
        handler = MaloneHandler()
        with person_logged_in(self.factory.makePerson()):
            mail_handled, add_comment_to_bug, commands = \
                handler.extractAndAuthenticateCommands(message,
                    'new@bugs.launchpad.net')
        self.assertEquals(mail_handled, None)
        self.assertEquals(map(str, commands), [
            'bug new',
            'affects malone',
            ])

    def test_mailToHelpFromUnknownUser(self):
        """Mail from people of no account to help@ is simply dropped.
        """
        message = self.factory.makeSignedMessage()
        handler = MaloneHandler()
        mail_handled, add_comment_to_bug, commands = \
            handler.extractAndAuthenticateCommands(message,
                'help@bugs.launchpad.net')
        self.assertEquals(mail_handled, True)
        self.assertEquals(self.getSentMail(), [])

    def test_mailToHelp(self):
        """Mail to help@ generates a help command."""
        message = self.factory.makeSignedMessage()
        handler = MaloneHandler()
        with person_logged_in(self.factory.makePerson()):
            mail_handled, add_comment_to_bug, commands = \
                handler.extractAndAuthenticateCommands(message,
                    'help@bugs.launchpad.net')
        self.assertEquals(mail_handled, True)
        self.assertEquals(len(self.getSentMail()), 1)
        # TODO: Check the right mail was sent. -- mbp 20100923

    def getSentMail(self):
        # Sending mail is (unfortunately) a side effect of parsing the
        # commands, and unfortunately you must commit the transaction to get
        # them sent.
        transaction.commit()
        return stub.test_emails[:]

    def switchDbUser(self, user):
        """Commit the transaction and switch to the new user."""
        transaction.commit()
        LaunchpadZopelessLayer.switchDbUser(user)

    def test_new_bug_big_body(self):
        # If a bug email is sent with an excessively large body, we email the
        # user back and ask that they use attachments instead.
        big_body_text = 'This is really big.' * 10000
        mail = self.factory.makeSignedMessage(body=big_body_text)
        self.switchDbUser(config.processmail.dbuser)
        # Rejection email goes to the preferred email of the current user.
        # The current user is extracted from the current interaction, which is
        # set up using the authenticateEmail method.  However that expects
        # real GPG signed emails, which we are faking here.
        login(mail['from'])
        handler = MaloneHandler()
        self.assertTrue(handler.process(mail,
            'new@bugs.launchpad.dev', None))
        notification = pop_notifications()[0]
        self.assertEqual('Submit Request Failure', notification['subject'])
        # The returned message is a multipart message, the first part is
        # the message, and the second is the original message.
        message, original = notification.get_payload()
        self.assertIn(
            "The description is too long.",
            message.get_payload(decode=True))


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
            handler.process(msg, msg['To'])
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
            handler.process(msg, msg['To'])
        commit()
        # Since there were no commands in the poorly-timestamped message, no
        # error emails were generated.
        self.assertEqual(stub.test_emails, [])
