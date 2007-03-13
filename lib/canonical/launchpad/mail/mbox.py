# Copyright 2007 Canonical Ltd.  All rights reserved.

"""An IMailer that stores messages in a specified mbox file."""


__metaclass__ = type


import email
import mailbox

from email.Utils import make_msgid
from logging import getLogger

from zope.app import zapi
from zope.app.mail.interfaces import IMailer
from zope.interface import implements

COMMASPACE = ', '


class MboxMailer:
    """
    Stores the message in a Unix mailbox file.  This will be so much cooler
    when we can use Python 2.5's mailbox module.
    """
    implements(IMailer)

    def __init__(self, filename, overwrite, mailer):
        self.filename = filename
        if overwrite:
            # Truncate existing file.  Subsequent opens will always append.
            # XXX should we open the file once here regardless?  IMailer does
            # not have a close() method, so no.
            try:
                fp = open(self.filename, 'w')
            finally:
                fp.close()
        self.mailer = mailer

    def send(self, fromaddr, toaddrs, message):
        env_recips = COMMASPACE.join(toaddrs)
        log = getLogger('canonical.launchpad.mail')
        log.info('Email from %s to %s being stored in mailbox %s',
                 fromaddr, env_recips, self.filename)
        msg = email.message_from_string(message)
        # Mimic what MTAs such as Postfix do in transfering the envelope
        # sender into the Return-Path header.  It's okay if the message has
        # multiple such headers.
        msg['Return-Path'] = fromaddr
        # Because it might be useful, copy the envelope recipients into the
        # RFC 2822 headers too.
        msg['X-Envelope-To'] = env_recips
        # Add the Message-ID required by the interface; even though the
        # interface says that the message text doesn't include such a header,
        # zap it first just in case.
        del msg['message-id']
        msg['Message-ID'] = message_id = make_msgid()
        fp = open(self.filename, 'a')
        try:
            print >> fp, msg
        finally:
            fp.close()
        sendmail = zapi.getUtility(IMailer, self.mailer)
        sendmail.send(fromaddr, toaddrs, message)
        return message_id
