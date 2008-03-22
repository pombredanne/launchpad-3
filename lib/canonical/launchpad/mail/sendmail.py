# Copyright 2005-2008 Canonical Ltd.  All rights reserved.

"""
The One True Way to send mail from the Launchpad application.

Uses zope.app.mail.interfaces.IMailer, so you can subscribe to
IMailSentEvent or IMailErrorEvent to record status.

TODO: We should append a signature to messages sent through
simple_sendmail and sendmail with a message explaining 'this
came from launchpad' and a link to click on to change their
messaging settings -- stub 2004-10-21

"""

__all__ = [
    'format_address',
    'sendmail',
    'simple_sendmail',
    'simple_sendmail_from_person',
    'raw_sendmail']

import sets
from email.Utils import make_msgid, formatdate, formataddr
from email.Message import Message
from email.Header import Header
from email.MIMEText import MIMEText
from email import Charset
from smtplib import SMTP

from zope.app import zapi
from zope.app.mail.interfaces import IMailDelivery
from zope.security.proxy import isinstance as zisinstance

from canonical.config import config
from canonical.lp import isZopeless
from canonical.launchpad.helpers import is_ascii_only
from canonical.launchpad.mail.stub import TestMailer

# email package by default ends up encoding UTF-8 messages using base64,
# which sucks as they look like spam to stupid spam filters. We define
# our own custom charset definition to force quoted printable.
del Charset.CHARSETS['utf-8']
Charset.add_charset('utf-8', Charset.SHORTEST, Charset.QP, 'utf-8')
Charset.add_alias('utf8', 'utf-8')

def do_paranoid_email_content_validation(from_addr, to_addrs, subject, body):
    """Validate various bits of the email.

    Extremely paranoid parameter checking is required to ensure we
    raise an exception rather than stick garbage in the mail
    queue. Currently, the Z3 mailer is too forgiving and accepts badly
    formatted emails which the delivery mechanism then can't send.

    An AssertionError will be raised if one of the parameters is
    invalid.
    """
    # XXX StuartBishop 2005-03-19:
    # These checks need to be migrated upstream if this bug
    # still exists in modern Z3.
    assert (zisinstance(to_addrs, (list, tuple, sets.Set, set))
            and len(to_addrs) > 0), 'Invalid To: %r' % (to_addrs,)
    assert zisinstance(from_addr, basestring), 'Invalid From: %r' % from_addr
    assert zisinstance(subject, basestring), 'Invalid Subject: %r' % subject
    assert zisinstance(body, basestring), 'Invalid body: %r' % body
    for addr in to_addrs:
        assert zisinstance(addr, basestring) and bool(addr), \
                'Invalid recipient: %r in %r' % (addr, to_addrs)

def format_address(name, address):
    r"""Formats a name and address to be used as an email header.

        >>> format_address('Name', 'foo@bar.com')
        'Name <foo@bar.com>'
        >>> format_address('', 'foo@bar.com')
        'foo@bar.com'
        >>> format_address(None, u'foo@bar.com')
        'foo@bar.com'

    It handles unicode and characters that need quoting as well.

        >>> format_address(u'F\xf4\xf4 Bar', 'foo.bar@canonical.com')
        '=?utf-8?b?RsO0w7QgQmFy?= <foo.bar@canonical.com>'

        >>> format_address('Foo [Baz] Bar', 'foo.bar@canonical.com')
        '"Foo \\[Baz\\] Bar" <foo.bar@canonical.com>'
    """
    if not name:
        return str(address)
    name = str(Header(name))
    return str(formataddr((name, address)))


def simple_sendmail(from_addr, to_addrs, subject, body, headers=None):
    """Send an email from from_addr to to_addrs with the subject and body
    provided. to_addrs can be a list, tuple, or ASCII string.

    Arbitrary headers can be set using the headers parameter. If the value for
    a given key in the headers dict is a list or tuple, the header will be
    added to the message once for each value in the list.  Note however that
    the `Precedence` header will always be set to `bulk`, overriding any
    `Precedence` header in `headers`.

    Returns the `Message-Id`.
    """
    if headers is None:
        headers = {}
    if zisinstance(to_addrs, basestring):
        to_addrs = [to_addrs]

    # It's the caller's responsibility to encode the address fields to
    # ASCII strings.
    # XXX CarlosPerelloMarin 2006-03-20: Spiv is working on fixing this
    # so we can provide a Unicode string and get the right encoding.
    for address in [from_addr] + list(to_addrs):
        if not isinstance(address, str) or not is_ascii_only(address):
            raise AssertionError(
                'Expected an ASCII str object, got: %r' % address)


    do_paranoid_email_content_validation(
        from_addr=from_addr, to_addrs=to_addrs, subject=subject, body=body)

    msg = MIMEText(body.encode('utf-8'), 'plain', 'utf-8')
    # The header_body_values may be a list or tuple of values, so we will add
    # a header once for each value provided for that header. (X-Launchpad-Bug,
    # for example, may often be set more than once for a bugmail.)
    for header, header_body_values in headers.items():
        if not zisinstance(header_body_values, (list, tuple)):
            header_body_values = [header_body_values]
        for header_body_value in header_body_values:
            msg[header] = header_body_value
    msg['To'] = ','.join(to_addrs)
    msg['From'] = from_addr
    msg['Subject'] = subject
    return sendmail(msg)


def simple_sendmail_from_person(
    person, to_addrs, subject, body, headers=None):
    """Sends a mail using the given person as the From address.

    It works just like simple_sendmail, excepts that it ensures that the
    From header is properly encoded.
    """
    from_addr = format_address(
        person.displayname, person.preferredemail.email)
    return simple_sendmail(
        from_addr, to_addrs, subject, body, headers=headers)


def sendmail(message, to_addrs=None):
    """Send an email.Message.Message

    If you just need to send dumb ASCII or Unicode, simple_sendmail
    will be easier for you. Sending attachments or multipart messages
    will need to use this method.

    From:, To: and Subject: headers should already be set.
    Message-Id:, Date:, and Reply-To: headers will be set if they are
    not already. Errors-To: and Return-Path: headers will always be set.
    The more we look valid, the less we look like spam.

    If to_addrs is None, the message will be sent to all the addresses
    specified in the To: and CC: headers.

    Uses zope.app.mail.interfaces.IMailer, so you can subscribe to
    IMailSentEvent or IMailErrorEvent to record status.

    Returns the Message-Id
    """
    assert isinstance(message, Message), 'Not an email.Message.Message'
    assert 'to' in message and bool(message['to']), 'No To: header'
    assert 'from' in message and bool(message['from']), 'No From: header'
    assert 'subject' in message and bool(message['subject']), \
            'No Subject: header'

    from_addr = message['from']
    if to_addrs is None:
        to_addrs = message['to'].split(',')
        if message['cc']:
            to_addrs = to_addrs + message['cc'].split(',')

    # Add a Message-Id: header if it isn't already there
    if 'message-id' not in message:
        message['Message-Id'] = make_msgid('launchpad@canonical')

    # Add a Date: header if it isn't already there
    if 'date' not in message:
        message['Date'] = formatdate()

    # Add a Reply-To: header if it isn't already there
    if 'reply-to' not in message:
        message['Reply-To'] = message['from']

    # Add a Sender: header to show that we were the one sending the
    # email.
    if "Sender" not in message:
        message["Sender"] = config.bounce_address

    # Add an Errors-To: header for bounce handling
    del message['Errors-To']
    message['Errors-To'] = config.bounce_address

    # Add a Return-Path: header for bounce handling as well. Normally
    # this is added by the SMTP mailer using the From: header. But we
    # want it to be bounce_address instead.
    if 'return-path' not in message:
        message['Return-Path'] = config.bounce_address

    # Add Precedence header to prevent automatic reply programs
    # (e.g. vacation) from trying to respond to our messages.
    del message['Precedence']
    message['Precedence'] = 'bulk'

    # Add an X-Generated-By header for easy whitelisting
    del message['X-Generated-By']
    message['X-Generated-By'] = 'Launchpad (canonical.com)'

    raw_message = message.as_string()
    if isZopeless():
        # Zopeless email sending is not unit tested, and won't be.
        # The zopeless specific stuff is pretty simple though so this
        # should be fine.

        if config.instance_name == 'testrunner':
            # when running in the testing environment, store emails
            TestMailer().send(config.bounce_address, to_addrs, raw_message)
        else:
            if config.zopeless.send_email:
                # Note that we simply throw away dud recipients. This is fine,
                # as it emulates the Z3 API which doesn't report this either
                # (because actual delivery is done later).
                smtp = SMTP(
                    config.zopeless.smtp_host, config.zopeless.smtp_port)

                # The "MAIL FROM" is set to the bounce address, to behave in a
                # way similar to mailing list software.
                smtp.sendmail(config.bounce_address, to_addrs, raw_message)
                smtp.quit()
        # Strip the angle brackets to the return a Message-Id consistent with
        # raw_sendmail (which doesn't include them).
        return message['message-id'][1:-1]
    else:
        # The "MAIL FROM" is set to the bounce address, to behave in a way
        # similar to mailing list software.
        return raw_sendmail(config.bounce_address, to_addrs, raw_message)


def raw_sendmail(from_addr, to_addrs, raw_message):
    """Send a raw RFC8222 email message.

    All headers and encoding should already be done, as the message is
    spooled out verbatim to the delivery agent.

    You should not need to call this method directly, although it may be
    necessary to pass on signed or encrypted messages.

    Returns the message-id.

    """
    assert not isinstance(to_addrs, basestring), 'to_addrs must be a sequence'
    assert isinstance(raw_message, str), 'Not a plain string'
    assert raw_message.decode('ascii'), 'Not ASCII - badly encoded message'
    mailer = zapi.getUtility(IMailDelivery, 'Mail')
    return mailer.send(from_addr, to_addrs, raw_message)


if __name__ == '__main__':
    from canonical.lp import initZopeless
    tm = initZopeless()
    simple_sendmail(
            'stuart.bishop@canonical.com', ['stuart@stuartbishop.net'],
            'Testing Zopeless', 'This is the body')
    tm.uninstall()

