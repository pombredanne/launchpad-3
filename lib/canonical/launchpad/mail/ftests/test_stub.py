import unittest
from zope.testing.doctest import DocTestSuite
from canonical.tests.functional import FunctionalTestSetup

from zope.app.tests.setup import placefulSetUp, placefulTearDown

import transaction

import email
from email.MIMEText import MIMEText
from canonical.launchpad.mail import *
from canonical.launchpad.mail import stub

def setUp(junk):
    stub.test_emails[:] = []
    FunctionalTestSetup().setUp()

def tearDown(junk):
    stub.test_emails[:] = []
    FunctionalTestSetup().tearDown()

def test_simple_sendmail():
    r"""
    Note that we are using the TestMailer, so first we need to reset the
    in-memory message store in case other tests have left a mess.

    Send an email (faked by TestMailer - no actual email is sent)

    >>> body = 'The email body'
    >>> subject = 'The email subject'
    >>> message_id = simple_sendmail(
    ...     'nobody@example.com', ['nobody2@example.com'], subject, body
    ...     )

    We should have a message id, a string

    >>> bool(message_id)
    True
    >>> isinstance(message_id, str)
    True

    The TestMailer stores sent emails in memory (which we cleared in the
    setUp() method). But the actual email has yet to be sent, as that 
    happens when the transaction is committed.

    >>> len(stub.test_emails)
    0
    >>> transaction.commit()
    >>> len(stub.test_emails)
    1
    
    >>> from_addr, to_addrs, raw_message = stub.test_emails.pop()
    >>> from_addr
    'nobody@example.com'
    >>> to_addrs
    ['nobody2@example.com']

    The message should be a sane RFC2822 document

    >>> message = email.message_from_string(raw_message, strict=True)
    >>> message['From']
    'nobody@example.com'
    >>> message['To']
    'nobody2@example.com'
    >>> message['Subject'] == subject
    True
    >>> message.get_payload() == body
    True

    """

def test_suite():
    suite = DocTestSuite(setUp=setUp, tearDown=tearDown)
    return suite

if __name__ == '__main__':
    unittest.main(test_suite())
