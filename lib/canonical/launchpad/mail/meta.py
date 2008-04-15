# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.app.component.metaconfigure import handler, utility
from zope.sendmail.interfaces import IMailer
from zope.sendmail.zcml import IMailerDirective
from zope.interface import Interface
from zope.schema import ASCII, Bool

from canonical.launchpad.interfaces import IMailBox
from canonical.launchpad.mail.stub import StubMailer, TestMailer
from canonical.launchpad.mail.mailbox import TestMailBox, POP3MailBox
from canonical.launchpad.mail.mbox import MboxMailer



class ITestMailBoxDirective(Interface):
    """Configure a mail box which operates on test_emails."""

def testMailBoxHandler(_context):
    utility(_context, IMailBox, component=TestMailBox())


class IPOP3MailBoxDirective(Interface):
    """Configure a mail box which interfaces to a POP3 server."""
    host = ASCII(
            title=u"Host",
            description=u"Host name of the POP3 server.",
            required=True,
            )

    user = ASCII(
            title=u"User",
            description=u"User name to connect to the POP3 server with.",
            required=True,
            )

    password = ASCII(
            title=u"Password",
            description=u"Password to connect to the POP3 server with.",
            required=True,
            )

    ssl = Bool(
            title=u"SSL",
            description=u"Use SSL.",
            required=False,
            default=False)

def pop3MailBoxHandler(_context, host, user, password, ssl=False):
    utility(
        _context, IMailBox, component=POP3MailBox( host, user, password, ssl))


class IStubMailerDirective(IMailerDirective):
    from_addr = ASCII(
            title=u"From Address",
            description=u"All outgoing emails will use this email address",
            required=True,
            )
    to_addr = ASCII(
            title=u"To Address",
            description=
                u"All outgoing emails will be redirected to this email address",
            required=True,
            )
    mailer = ASCII(
            title=u"Mailer to use",
            description=u"""\
                Which registered mailer to use, such as configured with
                the smtpMailer or sendmailMailer directives""",
                required=False,
                default='smtp',
                )
    rewrite = Bool(
            title=u"Rewrite headers",
            description=u"""\
                    If true, headers are rewritten in addition to the
                    destination address in the envelope. May me required
                    to bypass spam filters.""",
            required=False,
            default=False,
            )


def stubMailerHandler(
        _context, name, from_addr, to_addr, mailer='smtp', rewrite=False
        ):
    _context.action(
           discriminator = ('utility', IMailer, name),
           callable = handler,
           args = (
               'provideUtility',
               IMailer, StubMailer(from_addr, [to_addr], mailer, rewrite), name,
               )
           )


class ITestMailerDirective(IMailerDirective):
    pass

def testMailerHandler(_context, name):
    _context.action(
            discriminator = ('utility', IMailer, name),
            callable = handler,
            args = ('provideUtility', IMailer, TestMailer(), name,)
            )


class IMboxMailerDirective(IMailerDirective):
    filename = ASCII(
        title=u'File name',
        description=u'Unix mbox file to store outgoing emails in',
        required=True,
        )
    overwrite = Bool(
        title=u'Overwrite',
        description=u'Whether to overwrite the existing mbox file or not',
        required=False,
        default=False,
        )
    mailer = ASCII(
        title=u"Chained mailer to which messages are forwarded",
        description=u"""\
            Optional mailer to forward messages to, such as those configured
            with smtpMailer, sendmailMailer, or testMailer directives.  When
            not given, the message is not forwarded but only stored in the
            mbox file.""",
        required=False,
        default=None,
        )


def mboxMailerHandler(_context, name, filename, overwrite, mailer=None):
    _context.action(
        discriminator = ('utility', IMailer, name),
        callable = handler,
        args = ('provideUtility', IMailer,
                MboxMailer(filename, overwrite, mailer),
                name,)
        )
