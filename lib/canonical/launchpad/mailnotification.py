"""mailer.py -- Handle all mail notification done in the Launchpad
application."""

from zope.app import zapi
from zope.app.mail.interfaces import IMailDelivery
from canonical.launchpad.interfaces import IBug
from canonical.launchpad.mail import sendmail
from canonical.lp.dbschema import BugAssignmentStatus, BugPriority, \
     BugSeverity, BugInfestationStatus, BugExternalReferenceType

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

def notify_bug_assigned_package_added(event):
    """Notify CC'd list that this bug has been assigned to
    a source package."""
    pba = event.cause
    assignee_name = "(not assigned)"
    binary = "(none)"
    if pba.assignee:
        assignee_name = pba.assignee.displayname
    if pba.binarypackagename:
        binary = pba.binarypackagename.name

    msg = """\
Source Package: %(package)s
Binary: %(binary)s
Status: %(status)s
Priority: %(priority)s
Severity: %(severity)s
Assigned: %(assigned)s
""" % {'package' : pba.sourcepackage.sourcepackagename.name,
       'binary' : binary,
       'status' : BugAssignmentStatus.items[int(pba.bugstatus)].title,
       'priority' : BugPriority.items[int(pba.priority)].title,
       'severity' : BugSeverity.items[int(pba.severity)].title,
       'assigned' : assignee_name}

    sendmail(
        FROM_MAIL, get_cc_list(event.object),
        '"%s" package assignment' % event.object.title, msg)

def notify_bug_product_infestation_added(event):
    """Notify CC'd list that this bug has infested a
    product release."""
    bpi = event.cause

    msg = """\
Product: %(product)s
Infestation: %(infestation)s
""" % {'product' : bpi.productrelease.product.name + " " + bpi.productrelease.version,
       'infestation' : BugInfestationStatus.items[bpi.infestationstatus].title}

    sendmail(
        FROM_MAIL, get_cc_list(event.object),
        '"%s" product infestation' % event.object.title, msg)

def notify_bug_package_infestation_added(event):
    """Notify CC'd list that this bug has infested a
    source package release."""
    bpi = event.cause

    msg = """\
Source Package: %(package)s
Infestation: %(infestation)s
""" % {'package' :
         bpi.sourcepackagerelease.sourcepackage.name + " " +
         bpi.sourcepackagerelease.version,
       'infestation' : BugInfestationStatus.items[bpi.infestationstatus].title}

    sendmail(
        FROM_MAIL, get_cc_list(event.object),
        '"%s" package infestation' % event.object.title, msg)

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

def notify_bug_external_ref_added(event):
    """Notify CC'd list that a new external reference has
    been added for this bug."""
    ber = event.cause

    msg = """\
Bug Ref Type: %(ref_type)s
Data: %(data)s
Description: %(description)s
""" % {'ref_type' : BugExternalReferenceType.items[int(ber.bugreftype)].title,
       'data' : ber.data,
       'description' : ber.description}

    sendmail(
        FROM_MAIL, get_cc_list(event.object),
        '"%s" external reference added' % event.object.title, msg)

def notify_bug_watch_added(event):
    """Notify CC'd list that a new watch has been added for this
    bug."""
    bw = event.cause

    msg = """\
Bug Tracker: %(bug_tracker)s
Remote Bug: %(remote_bug)s
""" % {'bug_tracker' : bw.bugtracker.title, 'remote_bug' : bw.remotebug}

    sendmail(
        FROM_MAIL, get_cc_list(event.object),
        '"%s" watch added' % event.object.title, msg)
