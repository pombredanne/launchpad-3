from zope.app.component.metaconfigure import handler
from zope.app.mail.interfaces import IMailer
from zope.app.mail.metadirectives import IMailerDirective
from zope.schema import ASCII, Bool
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
        _context, name, from_addr, to_addr, mailer='sendmail', rewrite=False
        ):
    _context.action(
           discriminator = ('utility', IMailer, name),
           callable = handler,
           args = (
               'Utilities', 'provideUtility',
               IMailer, StubMailer(from_addr, [to_addr], mailer, rewrite), name,
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
