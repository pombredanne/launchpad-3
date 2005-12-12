# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Functions to accomodate testing of the email system."""

__all__ = ['read_test_message']

__metaclass__ = type

import email
import os.path

from canonical.launchpad.mail.signedmessage import SignedMessage

testmails_path = os.path.join(
                    os.path.dirname(__file__), 'emails') + os.path.sep

def read_test_message(filename):
    """Reads a test message and returns it as ISignedMessage.

    The test messages are located in canonical/launchpad/mail/ftests/emails
    """
    return email.message_from_file(
        open(testmails_path + filename), _class=SignedMessage)
