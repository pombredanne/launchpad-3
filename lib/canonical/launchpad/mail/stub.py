"""
A stub IMailer for use in development and unittests
"""

from zope.interface import implements
from zope.app.mail.interfaces import IMailer
from zope.app import zapi
from logging import getLogger

class StubMailer(object):
    """
    Overrides the from_addr and to_addrs arguments and passes the
    email on to the sendmail mailer
    """
    implements(IMailer)

    def __init__(self, from_addr, to_addrs):
        self.from_addr = from_addr
        self.to_addrs = to_addrs

    def send(self, from_addr, to_addrs, message):
        log = getLogger('canonical.launchpad.mail')
        log.info('Email from %s to %s being redirected to %s' % (
            from_addr, ','.join(to_addrs), ','.join(self.to_addrs)
            ))
        sendmail = zapi.getUtility(IMailer, 'sendmail')
        sendmail.send(self.from_addr, self.to_addrs, message)

test_emails = []
class TestMailer(object):
    """
    Stores (from_addr, to_addrs, message) in the test_emails module global list
    where unittests can examine them.

    Tests or their harnesses will need to clear out the test_emails list.
    """
    implements(IMailer)

    def send(self, from_addr, to_addrs, message):
        test_emails.append( (from_addr, to_addrs, message) )


