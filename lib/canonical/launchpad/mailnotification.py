"""mailer.py -- Handle all mail notification done in the Launchpad
application."""

from zope.app import zapi
from zope.app.mail.interfaces import IMailDelivery
from canonical.launchpad.interfaces import IBug
from canonical.launchpad.mail import sendmail
from canonical.lp.dbschema import BugAssignmentStatus, BugPriority, BugSeverity

FROM_MAIL = "noreply@bbnet.ca"

def get_cc_list(bug):
    """Return the list of people that are CC'd on this bug."""
    return ['test@bbnet.ca']

def notify_bug_assigned_product_added(event):
    """Notify CC'd list that this bug has been assigned to
    a product."""
    pba = event.cause
    assignee_name = "(not assigned)"
    if pba.assignee:
        assignee_name = pba.assignee.displayname
    msg = """\
Product: %(product)s
Status: %(status)s
Priority: %(priority)s
Severity: %(severity)s
Assigned: %(assigned)s
""" % {'product' : pba.product.displayname,
       'status' : BugAssignmentStatus.items[int(pba.bugstatus)].title,
       'priority' : BugPriority.items[int(pba.priority)].title,
       'severity' : BugSeverity.items[int(pba.severity)].title,
       'assigned' : assignee_name}

    sendmail(
        FROM_MAIL, get_cc_list(event.object),
        '"%s" product assignment' % event.object.title, msg)

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
