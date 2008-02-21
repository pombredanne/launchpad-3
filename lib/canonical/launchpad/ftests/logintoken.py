# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Helper functions for logintoken-related tests."""

import email, re


def get_token_url_from_email(email_msg):
    """Return the logintoken URL contained in the given email message."""
    msg = email.message_from_string(email_msg)
    return get_token_url_from_string(msg.get_payload())

def get_token_url_from_string(s):
    """Return the logintoken URL contained in the given string."""
    return re.findall(r'http.*/token/.*', s)[0]
