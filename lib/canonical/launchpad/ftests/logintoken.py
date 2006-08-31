# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import email, re


__all__ = []


def get_token_url_from_email(email_msg):
    msg = email.message_from_string(email_msg)
    body = msg.get_payload()
    return re.findall(r'http.*/token/.*', body)[0]

