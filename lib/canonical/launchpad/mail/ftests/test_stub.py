# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest
from zope.testing.doctest import DocTestSuite
from canonical.functional import FunctionalTestSetup

import transaction

import email
from email.MIMEText import MIMEText
from canonical.launchpad.mail import stub, simple_sendmail

def setUp(junk):
    # Reset the in-memory mail spool
    stub.test_emails[:] = []
    FunctionalTestSetup().setUp()

def tearDown(junk):
    stub.test_emails[:] = []
    FunctionalTestSetup().tearDown()

def test_simple_sendmail():
    r"""
    Send an email (faked by TestMailer - no actual email is sent)

    >>> body = 'The email body'
    >>> subject = 'The email subject'
    >>> message_id1 = simple_sendmail(
    ...     'nobody1@example.com', ['nobody2@example.com'], subject, body
    ...     )

    We should have a message id, a string

    >>> bool(message_id1)
    True
    >>> isinstance(message_id1,str)
    True

    We can also send arbitrary headers through. Note how Python's
    email package handles Message-Id headers

    >>> message_id2 = simple_sendmail(
    ...     'nobody@example.com', ['nobody2@example.com'], subject, body,
    ...     {'Message-Id': '<myMessageId>', 'X-Fnord': 'True'}
    ...     )
    >>> message_id2
    'myMessageId'

    The TestMailer stores sent emails in memory (which we cleared in the
    setUp() method). But the actual email has yet to be sent, as that 
    happens when the transaction is committed.

    >>> len(stub.test_emails)
    0
    >>> transaction.commit()
    >>> len(stub.test_emails)
    2
    >>> stub.test_emails[0] == stub.test_emails[1]
    False

    We have two emails, but we have no idea what order they are in!

    >>> from_addr, to_addrs, raw_message = stub.test_emails.pop()
    >>> if from_addr == 'nobody1@example.com':
    ...     from_addr, to_addrs, raw_message = stub.test_emails.pop()
    >>> from_addr
    'bounces@canonical.com'
    >>> to_addrs
    ['nobody2@example.com']

    The message should be a sane RFC2822 document

    >>> message = email.message_from_string(raw_message)
    >>> message['From']
    'nobody@example.com'
    >>> message['To']
    'nobody2@example.com'
    >>> message['Subject'] == subject
    True
    >>> message['Message-Id']
    '<myMessageId>'
    >>> message.get_payload() == body
    True

    """

def test_suite():
    suite = DocTestSuite(setUp=setUp, tearDown=tearDown)
    return suite

if __name__ == '__main__':
    unittest.main(test_suite())
