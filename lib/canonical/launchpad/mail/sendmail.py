"""
The One True Way to send mail from the Launchpad application.

Uses zope.app.mail.interfaces.IMailer, so you can subscribe to
IMailSentEvent or IMailErrorEvent to record status.

TODO: We should append a signature to messages sent through
simple_sendmail and sendmail with a message explaining 'this
came from launchpad' and a link to click on to change their
messaging settings -- stub 2004-10-21

"""

__all__ = ['sendmail', 'simple_sendmail', 'raw_sendmail']

import sets
from email.Utils import make_msgid, formatdate, parseaddr, formataddr
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

# email package by default ends up encoding UTF8 messages using base64,
# which sucks as they look like spam to stupid spam filters. We define
# our own custom charset definition to force quoted printable.
Charset.add_charset('utf8', Charset.QP, Charset.QP, 'utf8')

def encode_address_field(address_field):
    """Encodes an address field according to RFC 2047.

    An address field can look like either:

        Some Name <someaddress>

    or:

        someaddress

    Only 'Some Name' should be encoded.
    """
    name, address = parseaddr(address_field)
    return formataddr((str(Header(name)), str(address)))


def do_paranoid_email_content_validation(from_addr, to_addrs, subject, body):
    """Validate various bits of the email.

    Extremely paranoid parameter checking is required to ensure we
    raise an exception rather than stick garbage in the mail
    queue. Currently, the Z3 mailer is too forgiving and accepts badly
    formatted emails which the delivery mechanism then can't send.

    An AssertionError will be raised if one of the parameters is
    invalid.
    """
    # XXX: These checks need to be migrated upstream if this bug
    # still exists in modern Z3 -- StuartBishop 20050319
    assert (zisinstance(to_addrs, (list, tuple, sets.Set, set))
            and len(to_addrs) > 0), 'Invalid To: %r' % (to_addrs,)
    assert zisinstance(from_addr, basestring), \
            'Invalid From: %r' % (from_addr,)
    assert zisinstance(subject, basestring), \
            'Invalid Subject: %r' % (from_addr,)
    assert zisinstance(body, basestring), 'Invalid body: %r' % (from_addr,)
    for addr in to_addrs:
        assert zisinstance(addr, basestring) and bool(addr), \
                'Invalid recipient: %r in %r' % (addr, to_addrs)


def simple_sendmail(from_addr, to_addrs, subject, body, headers={}):
    """Send an email from from_addr to to_addrs with the subject and body
    provided. to_addrs can be a list, tuple, or ASCII/Unicode string.

    Arbitrary headers can be set using the headers parameter. If the value for a
    given key in the headers dict is a list or tuple, the header will be added
    to the message once for each value in the list.

    Returns the Message-Id.
    """
    if zisinstance(to_addrs, basestring):
        to_addrs = [to_addrs]

    do_paranoid_email_content_validation(
        from_addr=from_addr, to_addrs=to_addrs, subject=subject, body=body)

    msg = MIMEText(body.encode('utf8'), 'plain', 'utf8')
    # The header_body_values may be a list or tuple of values, so we will add a
    # header once for each value provided for that header. (X-Launchpad-Bug,
    # for example, may often be set more than once for a bugmail.)
    for header, header_body_values in headers.items():
        if not zisinstance(header_body_values, (list, tuple)):
            header_body_values = [header_body_values]
        for header_body_value in header_body_values:
            msg[header] = header_body_value
    msg['To'] = ','.join([encode_address_field(addr) for addr in to_addrs])
    msg['From'] = encode_address_field(from_addr)
    msg['Subject'] = subject
    return sendmail(msg)


def sendmail(message):
    """Send an email.Message.Message

    If you just need to send dumb ASCII or Unicode, simple_sendmail
    will be easier for you. Sending attachments or multipart messages
    will need to use this method.

    From:, To: and Subject: headers should already be set.
    Message-Id:, Date:, and Reply-To: headers will be set if they are
    not already. Errors-To: and Return-Path: headers will always be set.
    The more we look valid, the less we look like spam.

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

    # Add an Errors-To: header for bounce handling
    del message['Errors-To']
    message['Errors-To'] = config.bounce_address

    # Add a Return-Path: header for bounce handling as well. Normally
    # this is added by the SMTP mailer using the From: header. But we
    # want it to be bounce_address instead.
    if 'return-path' not in message:
        message['Return-Path'] = config.bounce_address

    # Add an X-Generated-By header for easy whitelisting
    del message['X-Generated-By']
    message['X-Generated-By'] = 'Launchpad (canonical.com)'

    raw_message = message.as_string()
    if isZopeless():
        # Zopeless email sending is not unit tested, and won't be.
        # The zopeless specific stuff is pretty simple though so this
        # should be fine.
        if config.zopeless.send_email:
            # Note that we simply throw away dud recipients. This is fine,
            # as it emulates the Z3 API which doesn't report this either
            # (because actual delivery is done later).
            smtp = SMTP(config.zopeless.smtp_host, config.zopeless.smtp_port)

            # The "MAIL FROM" is set to the bounce address, to behave in a way
            # similar to mailing list software.
            smtp.sendmail(config.bounce_address, to_addrs, raw_message)
            smtp.quit()
        return message['message-id']
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

