"""mailer.py -- Handle all mail notification done in the Launchpad
application."""

from zope.app import zapi
from zope.app.mail.interfaces import IMailDelivery
from canonical.launchpad.interfaces import IBug
from canonical.launchpad.mail import simple_sendmail
from canonical.launchpad.database import BugTracker
from canonical.lp.dbschema import BugAssignmentStatus, BugPriority, \
     BugSeverity, BugInfestationStatus, BugExternalReferenceType
from canonical.launchpad.vocabularies import BugTrackerVocabulary

FROM_MAIL = "noreply@bbnet.ca"
#FROM_MAIL = "stuart@stuartbishop.net"

def get_cc_list(bug):
    """Return the list of people that are CC'd on this bug."""
    #return ["stuart@stuartbishop.net"]
    return ['test@bbnet.ca']

def notify_bug_assigned_product_added(product_assignment, event):
    """Notify CC'd list that this bug has been assigned to
    a product."""
    product_assignment = event.object
    assignee_name = "(not assigned)"
    if product_assignment.assignee:
        assignee_name = product_assignment.assignee.displayname
    msg = """\
Product: %(product)s
Status: %(status)s
Priority: %(priority)s
Severity: %(severity)s
Assigned: %(assigned)s
""" % {'product' : product_assignment.product.displayname,
       'status' : BugAssignmentStatus.items[int(product_assignment.bugstatus)].title,
       'priority' : BugPriority.items[int(product_assignment.priority)].title,
       'severity' : BugSeverity.items[int(product_assignment.severity)].title,
       'assigned' : assignee_name}

    simple_sendmail(
        FROM_MAIL, get_cc_list(product_assignment.bug),
        '"%s" product assignment' % product_assignment.bug.title, msg)

def notify_bug_assigned_product_modified(modified_product_assignment, event):
    """Notify CC'd list that this bug product assignment has been
    modified, describing what the changes were."""
    change = {}
    for name in event.edited_fields:
        old_val = getattr(event.object_before_modification, name)
        new_val = getattr(event.object, name)

        if old_val != new_val:
            change[name] = {}
            change[name]["old"] = old_val
            change[name]["new"] = new_val

    msg = """\
The following changes were made:

"""
    for changed_field in change.keys():
        msg += "%s: %s => %s\n" % (
            changed_field, change[changed_field]["old"], change[changed_field]["new"])

    simple_sendmail(
        FROM_MAIL, get_cc_list(modified_product_assignment.bug),
        '"%s" was modified' % modified_product_assignment.bug.title, msg)

def notify_bug_assigned_package_added(package_assignment, event):
    """Notify CC'd list that this bug has been assigned to
    a source package."""
    assignee_name = "(not assigned)"
    binary = "(none)"
    if package_assignment.assignee:
        assignee_name = package_assignment.assignee.displayname
    if package_assignment.binarypackagename:
        binary = package_assignment.binarypackagename.name

    msg = """\
Source Package: %(package)s
Binary: %(binary)s
Status: %(status)s
Priority: %(priority)s
Severity: %(severity)s
Assigned: %(assigned)s
""" % {'package' : package_assignment.sourcepackage.sourcepackagename.name,
       'binary' : binary,
       'status' : BugAssignmentStatus.items[int(package_assignment.bugstatus)].title,
       'priority' : BugPriority.items[int(package_assignment.priority)].title,
       'severity' : BugSeverity.items[int(package_assignment.severity)].title,
       'assigned' : assignee_name}

    simple_sendmail(
        FROM_MAIL, get_cc_list(package_assignment.bug),
        '"%s" package assignment' % package_assignment.bug.title, msg)

def notify_bug_product_infestation_added(product_infestation, event):
    """Notify CC'd list that this bug has infested a
    product release."""
    msg = """\
Product: %(product)s
Infestation: %(infestation)s
""" % {'product' :
         product_infestation.productrelease.product.name + " " +
         product_infestation.productrelease.version,
       'infestation' : BugInfestationStatus.items[product_infestation.infestationstatus].title}

    simple_sendmail(
        FROM_MAIL, get_cc_list(product_infestation.bug),
        '"%s" product infestation' % product_infestation.bug.title, msg)

def notify_bug_package_infestation_added(package_infestation, event):
    """Notify CC'd list that this bug has infested a
    source package release."""
    msg = """\
Source Package: %(package)s
Infestation: %(infestation)s
""" % {'package' :
         package_infestation.sourcepackagerelease.sourcepackage.name + " " +
         package_infestation.sourcepackagerelease.version,
       'infestation' : BugInfestationStatus.items[package_infestation.infestationstatus].title}

    simple_sendmail(
        FROM_MAIL, get_cc_list(package_infestation.bug),
        '"%s" package infestation' % package_infestation.bug.title, msg)

def notify_bug_comment_added(comment, event):
    """Notify CC'd list that a comment was added to this bug."""
    msg = """\
%s said:

%s

%s""" % (comment.owner.displayname,
         comment.title,
         comment.contents)

    simple_sendmail(
        FROM_MAIL, get_cc_list(comment.bug),
        'Comment on "%s"' % comment.bug.title, msg)

def notify_bug_external_ref_added(ext_ref, event):
    """Notify CC'd list that a new external reference has
    been added for this bug."""
    msg = """\
Bug Ref Type: %(ref_type)s
Data: %(data)s
Description: %(description)s
""" % {'ref_type' : BugExternalReferenceType.items[int(ext_ref.bugreftype)].title,
       'data' : ext_ref.data,
       'description' : ext_ref.description}

    simple_sendmail(
        FROM_MAIL, get_cc_list(ext_ref.bug),
        '"%s" external reference added' % ext_ref.bug.title, msg)

def notify_bug_watch_added(watch, event):
    """Notify CC'd list that a new watch has been added for this
    bug."""
    msg = """\
Bug Tracker: %(bug_tracker)s
Remote Bug: %(remote_bug)s
""" % {'bug_tracker' : watch.bugtracker.title, 'remote_bug' : watch.remotebug}

    simple_sendmail(
        FROM_MAIL, get_cc_list(watch.bug),
        '"%s" watch added' % watch.bug.title, msg)

def notify_bug_watch_modified(modified_bug_watch, event):
    orig = event.object_before_modification
    new = event.object

    btv = BugTrackerVocabulary(modified_bug_watch.bug)
    change = {}
    old_bt = getattr(orig, "bugtracker")
    new_bt = getattr(new, "bugtracker")
    if old_bt != new_bt:
        change["bugtracker"] = {}
        change["bugtracker"]["old"] = btv.getTermByToken(old_bt.id).title
        change["bugtracker"]["new"] = btv.getTermByToken(new_bt.id).title

    old_rb = getattr(orig, "remotebug")
    new_rb = getattr(new, "remotebug")
    if old_rb != new_rb:
        change["remotebug"] = {}
        change["remotebug"]["old"] = old_rb
        change["remotebug"]["new"] = new_rb

    msg = """The following changes were made:

"""
    for changed_field in change.keys():
        msg += "%s: %s => %s\n" % (
            changed_field, change[changed_field]["old"], change[changed_field]["new"])

    simple_sendmail(
        FROM_MAIL, get_cc_list(modified_bug_watch.bug),
        '"%s" was modified' % modified_bug_watch.bug.title, msg)

