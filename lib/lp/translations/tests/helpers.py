# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helper module reused in different tests."""

__metaclass__ = type

__all__ = [
    'print_mail_subject_and_body'
    ]

import email

def print_mail_subject_and_body(contents):
    msg = email.message_from_string(contents)
    body = msg.get_payload()
    print 'Subject: %s' % (msg['subject'])
    for line in body.split('\n'):
        print ">", line
