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

def send_edit_notification(from_addr, to_addrs, subject, edit_header_line,
                           changes):
    if changes:
        msg = """%s

The following changes were made:

""" % edit_header_line
        for changed_field in changes.keys():
            msg += "%s: %s => %s\n" % (
                changed_field, changes[changed_field]["old"], changes[changed_field]["new"])

        simple_sendmail(from_addr, to_addrs, subject, msg)

def get_cc_list(bug):
    """Return the list of people that are CC'd on this bug."""
    return ['test@bbnet.ca']

def get_changes(before, after, fields):
    """Return what changed from the object before to after for the
    passed-in fields. fields is a tuple of (field_name, display_value_func)
    tuples, where display_value_func is used to convert the differences
    in attribute values into something you could display in, for example,
    a change notification email."""
    changes = {}

    for field_name, display_value_func in fields:
        old_val = getattr(before, field_name, None)
        new_val = getattr(after, field_name, None)
        if old_val != new_val:
            changes[field_name] = {}
            if display_value_func:
                changes[field_name]['old'] = display_value_func(old_val)
                changes[field_name]['new'] = display_value_func(new_val)
            else:
                changes[field_name]['old'] = old_val
                changes[field_name]['new'] = new_val

    return changes

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
    changes = get_changes(
        before = event.object_before_modification,
        after = event.object,
        fields = (
            ("product", lambda v: v.displayname),
            ("bugstatus", lambda v: BugAssignmentStatus.items[v].title),
            ("priority", lambda v: BugPriority.items[v].title),
            ("severity", lambda v: BugSeverity.items[v].title),
            ("assignee", lambda v: v.displayname)))

    send_edit_notification(
        from_addr = FROM_MAIL,
        to_addrs = get_cc_list(modified_product_assignment.bug),
        subject = '"%s" product assignment edited' % modified_product_assignment.bug.title,
        edit_header_line = (
            "Edited assignment to product: %s" %
            modified_product_assignment.product.displayname),
        changes = changes)

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

def notify_bug_assigned_package_modified(modified_package_assignment, event):
    """Notify CC'd list that something had been changed about this bug
    package assignment."""
    changes = get_changes(
        before = event.object_before_modification,
        after = event.object,
        fields = (
            ("bugstatus", lambda v: BugAssignmentStatus.items[v].title),
            ("priority", lambda v: BugPriority.items[v].title),
            ("severity", lambda v: BugSeverity.items[v].title),
            ("binarypackagename", lambda v: v.name),
            ("assignee", lambda v: v.displayname)))

    send_edit_notification(
        from_addr = FROM_MAIL,
        to_addrs = get_cc_list(modified_package_assignment.bug),
        subject = '"%s" package assignment edited' % modified_package_assignment.bug.title,
        edit_header_line = (
            "Edited assignment to package: %s" %
            modified_package_assignment.sourcepackage.sourcepackagename.name),
        changes = changes)

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

def notify_bug_product_infestation_modified(modified_product_infestation, event):
    """Notify CC'd list that this product infestation has been edited."""
    changes = get_changes(
        before = event.object_before_modification,
        after = event.object,
        fields = (
            ("productrelease", lambda v: "%s %s" % (
                v.product.name, v.version)),
            ("infestationstatus", lambda v: BugInfestationStatus.items[v].title)))

    send_edit_notification(
        from_addr = FROM_MAIL,
        to_addrs = get_cc_list(modified_product_infestation.bug),
        subject = (
            '"%s" product infestation edited' %
            event.object_before_modification.bug.title),
        edit_header_line = (
            "Edited infested product: %s" %
            event.object_before_modification.productrelease.product.displayname + " " +
            event.object_before_modification.productrelease.version),
        changes = changes)

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

def notify_bug_package_infestation_modified(modified_package_infestation, event):
    """Notify CC'd list that this package infestation has been modified."""
    changes = get_changes(
        before = event.object_before_modification,
        after = event.object,
        fields = (
            ("sourcepackagerelease", lambda v: "%s %s" % (v.name, v.version)),
            ("infestationstatus", lambda v: BugInfestationStatus.items[v].title)))

    send_edit_notification(
        from_addr = FROM_MAIL,
        to_addrs = get_cc_list(modified_package_infestation.bug),
        subject = '"%s" package infestation edited' % modified_package_infestation.bug.title,
        edit_header_line = (
            "Edited infested package: %s" %
            event.object_before_modification.sourcepackagerelease.sourcepackage.sourcepackagename.name + " " +
            event.object_before_modification.sourcepackagerelease.version),
        changes = changes)

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
    btv = BugTrackerVocabulary(modified_bug_watch.bug)
    changes = get_changes(
        before = event.object_before_modification,
        after = event.object,
        fields = (
            ("bugtracker", lambda v: btv.getTermByToken(v.id).title),
            ("remotebug", lambda v: v)))

    send_edit_notification(
        from_addr = FROM_MAIL,
        to_addrs = get_cc_list(modified_bug_watch.bug),
        subject = '"%s" watch edited' % event.object_before_modification.bug.title,
        edit_header_line = (
            "Edited watch on bugtracker: %s" %
            event.object_before_modification.bugtracker.title),
        changes = changes)
