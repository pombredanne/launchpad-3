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

from email.Utils import make_msgid, formatdate
from email.Message import Message
from email.MIMEText import MIMEText
#from email.Charset import Charset, QP
from email import Charset
from zope.app import zapi
from zope.app.mail.interfaces import IMailDelivery

# email package by default ends up encoding UTF8 messages using base64,
# which sucks as they look like spam to stupid spam filters. We define
# our own custom charset definition to force quoted printable.
Charset.add_charset('utf8', Charset.QP, Charset.QP, 'utf8')

def simple_sendmail(from_addr, to_addrs, subject, body, headers={}):
    """Send an email from from_addr to to_addrs with the subject and body
    provided. to_addrs can be a list, tuple, or ASCII/Unicode string.

    Arbitrary headers can be set using the headers parameter.
   
    Returns the Message-Id.
    """
    if not isinstance(to_addrs, (list, tuple)):
        to_addrs = [to_addrs]

    msg = MIMEText(body.encode('utf8'), 'plain', 'utf8')
    for k,v in headers.items():
        del msg[k]
        msg[k] = v
    msg['To'] = ','.join([str(a) for a in to_addrs])
    msg['From'] = from_addr
    msg['Subject'] = subject
    return sendmail(msg)

def sendmail(message):
    """Send an email.Message.Message

    If you just need to send dumb ASCII or Unicode, simple_sendmail
    will be easier for you. Sending attachments or multipart messages
    will need to use this method.

    From:, To: and Subject: headers should already be set.
    Message-Id:, Date:, and Reply-To: headers will be set if they are 
    not already. Errors-To: headers will always be set. The more we look
    valid, the less we look like spam.
    
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

    # Add an Errors-To: header for future bounce handling
    # Currently bounces@canonical.com silently drops them.
    del message['Errors-To']
    message['Errors-To'] = 'bounces@canonical.com'

    # Add an X-Generated-By header for easy whitelisting
    del message['X-Generated-By']
    message['X-Generated-By'] = 'Launchpad (canonical.com)'

    return raw_sendmail(from_addr, to_addrs, message.as_string())

def raw_sendmail(from_addr, to_addrs, raw_message):
    """Send a raw RFC8222 email message. 
    
    All headers and encoding should already be done, as the message is
    spooled out verbatim to the delivery agent.

    You should not need to call this method directly, although it may be
    necessary to pass on signed or encrypted messages.

    Returns the message-id

    """
    assert not isinstance(to_addrs, basestring), 'to_addrs must be a sequence'
    assert isinstance(raw_message, str), 'Not a plain string'
    assert raw_message.decode('ascii'), 'Not ASCII - badly encoded message'
    mailer = zapi.getUtility(IMailDelivery, 'Mail')
    return mailer.send(from_addr, to_addrs, raw_message)

