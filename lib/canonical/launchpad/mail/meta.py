from zope.app.component.metaconfigure import handler
from zope.app.mail.interfaces import IMailer
from zope.app.mail.metadirectives import IMailerDirective
from zope.schema import ASCII
from stub import StubMailer, TestMailer

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
                default='sendmail',
                )


def stubMailerHandler(_context, name, from_addr, to_addr, mailer='sendmail'):
    _context.action(
           discriminator = ('utility', IMailer, name),
           callable = handler,
           args = (
               'Utilities', 'provideUtility',
               IMailer, StubMailer(from_addr, [to_addr], mailer), name,
               )
           )

class ITestMailerDirective(IMailerDirective):
    pass

def testMailerHandler(_context, name):
    _context.action(
            discriminator = ('utility', IMailer, name),
            callable = handler,
            args = (
                'Utilities', 'provideUtility', IMailer, TestMailer(), name,
                )
            )
