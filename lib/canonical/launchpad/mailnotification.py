"""mailer.py -- Handle all mail notification done in the Launchpad
application."""

from zope.app import zapi
from zope.app.mail.interfaces import IMailDelivery
from canonical.launchpad.interfaces import IBug
from canonical.launchpad.mail import sendmail

FROM_MAIL = "noreply@bbnet.ca"

def get_cc_list(bug):
    """Return the list of people that are CC'd on this bug."""
    return ['test@bbnet.ca']

def notify_bug_comment_added(event):
    """Notify CC'd list that a comment was added to this bug."""
    msg = """\
%s said:

%s

%s""" % (event.cause.owner.displayname,
         event.cause.title,
         event.cause.contents)

    sendmail(
        FROM_MAIL, get_cc_list(event.object),
        'Comment on "%s"' % event.object.title, msg)
