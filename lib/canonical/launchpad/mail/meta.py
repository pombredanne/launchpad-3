from zope.app.component.metaconfigure import handler
from zope.app.mail.interfaces import IMailer
from zope.app.mail.metadirectives import IMailerDirective
from zope.schema import ASCII
from stub import StubMailer

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

def stubMailerHandler(_context, name, from_addr, to_addr):
    _context.action(
           discriminator = ('utility', IMailer, name),
           callable = handler,
           args = (
               'Utilities', 'provideUtility',
               IMailer, StubMailer(from_addr, [to_addr]), name,
               )
           )

