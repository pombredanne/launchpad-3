"""mailer.py -- Handle all mail notification done in the Launchpad
application."""

from zope.app import zapi
from zope.app.mail.interfaces import IMailDelivery

from canonical.launchpad.interfaces import IBug, IBugSubscriptionSet
from canonical.launchpad.mail import simple_sendmail
from canonical.launchpad.database import Bug, BugTracker, EmailAddress
from canonical.lp.dbschema import BugTaskStatus, BugPriority, \
     BugSeverity, BugInfestationStatus, BugExternalReferenceType, \
     BugSubscription
from canonical.launchpad.vocabularies import BugTrackerVocabulary

FROM_ADDR = "Malone Bugtracker <noreply@canonical.com>"
GLOBAL_NOTIFICATION_EMAIL_ADDRS = ("global@bbnet.ca", "dilys@muse.19inch.net")
CC = "CC"

def send_edit_notification_simple(bug, from_addr, to_addrs, subject, message):
    '''Simple wrapper around simple_sendmail that prepends the id of the bug
    passed in to the subject of the message.'''
    subject = "Bug #%d: %s" % (bug.id, subject)
    simple_sendmail(
        from_addr, to_addrs, subject, subject + "\n\n" + message)

def send_edit_notification(bug, from_addr, to_addrs, subject, edit_header_line,
                      changes):
    if changes:
        msg = """%s

The following changes were made:

""" % edit_header_line
        for changed_field in changes.keys():
            msg += "%s: %s => %s\n" % (
                changed_field, changes[changed_field]["old"], changes[changed_field]["new"])

        send_edit_notification_simple(bug, from_addr, to_addrs, subject, msg)

def get_cc_list(bug):
    """Return the list of people that are CC'd on this bug."""
    bugsubscriptions = zapi.getAdapter(bug, IBugSubscriptionSet, "")
    return list(GLOBAL_NOTIFICATION_EMAIL_ADDRS) + bugsubscriptions.getCcEmailAddresses()

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

def notify_bug_added(bug_add_form, event):
    """Notify the owner and the global notification list that a bug
    was added."""
    owner = "(no owner)"
    spname = "(none)"
    pname = "(none)"
    if getattr(bug_add_form, 'owner', None):
        owner = bug_add_form.owner.displayname
    if getattr(bug_add_form, 'sourcepackagename', None):
        spname = bug_add_form.sourcepackagename.name
    if getattr(bug_add_form, 'product', None):
        pname = bug_add_form.product.displayname

    msg = """\
Title: %(title)s
Comment: %(comment)s
Source Package: %(source_package)s
Product: %(product)s
Submitted By: %(owner)s
""" % {'title' : bug_add_form.title,
       'comment' : bug_add_form.comment,
       'source_package' : spname,
       'product' : pname,
       'owner' : owner}

    bug = Bug.get(bug_add_form.id)
    send_edit_notification_simple(
        bug,
        FROM_ADDR,
        get_cc_list(bug),
        '"%s" added' % bug.title, msg)

def notify_bug_modified(modified_bug, event):
    """Notify the Cc'd list that this bug has been modified."""
    changes = get_changes(
        before = event.object_before_modification,
        after = event.object,
        fields = (
            ("title", None),
            ("shortdesc", None),
            ("description", None),
            ("name", None)))

    send_edit_notification(
        bug = modified_bug,
        from_addr = FROM_ADDR,
        to_addrs = get_cc_list(modified_bug),
        subject = '"%s" edited' % event.object_before_modification.title,
        edit_header_line = (
            "Edited bug: %s" % event.object_before_modification.title),
        changes = changes)

def notify_bug_assigned_product_added(product_task, event):
    """Notify CC'd list that this bug has been assigned to
    a product."""
    product_task = event.object
    assignee_name = "(not assigned)"
    if product_task.assignee:
        assignee_name = product_task.assignee.displayname
    msg = """\
Product: %(product)s
Status: %(status)s
Priority: %(priority)s
Severity: %(severity)s
Assigned: %(assigned)s
""" % {'product' : product_task.product.displayname,
       'status' : BugTaskStatus.items[int(product_task.bugstatus)].title,
       'priority' : BugPriority.items[int(product_task.priority)].title,
       'severity' : BugSeverity.items[int(product_task.severity)].title,
       'assigned' : assignee_name}

    send_edit_notification_simple(
        product_task.bug,
        FROM_ADDR, get_cc_list(product_task.bug),
        '"%s" assigned to product' % product_task.bug.title, msg)

def notify_bug_assigned_product_modified(modified_product_task, event):
    """Notify CC'd list that this bug product task has been
    modified, describing what the changes were."""
    changes = get_changes(
        before = event.object_before_modification,
        after = event.object,
        fields = (
            ("product", lambda v: v.displayname),
            ("bugstatus", lambda v: BugTaskStatus.items[v].title),
            ("priority", lambda v: BugPriority.items[v].title),
            ("severity", lambda v: BugSeverity.items[v].title),
            ("assignee", lambda v: (v and v.displayname) or "(not assigned)")))

    send_edit_notification(
        bug = modified_product_task.bug,
        from_addr = FROM_ADDR,
        to_addrs = get_cc_list(modified_product_task.bug),
        subject = '"%s" product task edited' % modified_product_task.bug.title,
        edit_header_line = (
            "Edited task for product: %s" %
            modified_product_task.product.displayname),
        changes = changes)

def notify_bug_assigned_package_added(package_task, event):
    """Notify CC'd list that this bug has been assigned to
    a source package."""
    assignee_name = "(not assigned)"
    binary = "(none)"
    if package_task.assignee:
        assignee_name = package_task.assignee.displayname
    if package_task.binarypackagename:
        binary = package_task.binarypackagename.name

    msg = """\
Source Package: %(package)s
Binary: %(binary)s
Status: %(status)s
Priority: %(priority)s
Severity: %(severity)s
Assigned: %(assigned)s
""" % {'package' : package_task.sourcepackage.sourcepackagename.name,
       'binary' : binary,
       'status' : BugTaskStatus.items[int(package_task.bugstatus)].title,
       'priority' : BugPriority.items[int(package_task.priority)].title,
       'severity' : BugSeverity.items[int(package_task.severity)].title,
       'assigned' : assignee_name}

    send_edit_notification_simple(
        package_task.bug,
        FROM_ADDR, get_cc_list(package_task.bug),
        '"%s" assigned to package' % package_task.bug.title, msg)

def notify_bug_assigned_package_modified(modified_package_task, event):
    """Notify CC'd list that something had been changed about this bug
    package task."""
    changes = get_changes(
        before = event.object_before_modification,
        after = event.object,
        fields = (
            ("bugstatus", lambda v: BugTaskStatus.items[v].title),
            ("priority", lambda v: BugPriority.items[v].title),
            ("severity", lambda v: BugSeverity.items[v].title),
            ("binarypackagename", lambda v: (v and v.name) or "(none)"),
            ("assignee", lambda v: (v and v.displayname) or "(not assigned)")))

    send_edit_notification(
        bug = modified_package_task.bug,
        from_addr = FROM_ADDR,
        to_addrs = get_cc_list(modified_package_task.bug),
        subject = '"%s" package task edited' % modified_package_task.bug.title,
        edit_header_line = (
            "Edited task for package: %s" %
            modified_package_task.sourcepackage.sourcepackagename.name),
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

    send_edit_notification_simple(
        product_infestation.bug,
        FROM_ADDR, get_cc_list(product_infestation.bug),
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
        bug = modified_product_infestation.bug,
        from_addr = FROM_ADDR,
        to_addrs = get_cc_list(modified_product_infestation.bug),
        subject = (
            '"%s" product infestation edited' %
            modified_product_infestation.bug.title),
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

    send_edit_notification_simple(
        package_infestation.bug,
        FROM_ADDR, get_cc_list(package_infestation.bug),
        '"%s" package infestation' % package_infestation.bug.title, msg)

def notify_bug_package_infestation_modified(modified_package_infestation, event):
    """Notify CC'd list that this package infestation has been modified."""
    changes = get_changes(
        before = event.object_before_modification,
        after = event.object,
        fields = (
            ("sourcepackagerelease", lambda v: "%s %s" % (
                v.sourcepackage.sourcepackagename.name, v.version)),
            ("infestationstatus", lambda v: BugInfestationStatus.items[v].title)))

    send_edit_notification(
        bug = modified_package_infestation.bug,
        from_addr = FROM_ADDR,
        to_addrs = get_cc_list(modified_package_infestation.bug),
        subject = '"%s" package infestation edited' % modified_package_infestation.bug.title,
        edit_header_line = (
            "Edited infested package: %s" %
            event.object_before_modification.sourcepackagerelease.sourcepackage.sourcepackagename.name + " " +
            event.object_before_modification.sourcepackagerelease.version),
        changes = changes)

def notify_bug_comment_added(bugmessage, event):
    """Notify CC'd list that a message was added to this bug."""
    msg = """\
%s said:

%s

%s""" % (bugmessage.message.owner.displayname,
         bugmessage.message.title,
         bugmessage.message.contents)

    send_edit_notification_simple(
        bugmessage.bug,
        FROM_ADDR, get_cc_list(bugmessage.bug),
        '"%s" comment added' % bugmessage.bug.title, msg)

def notify_bug_external_ref_added(ext_ref, event):
    """Notify CC'd list that a new web link has
    been added for this bug."""
    msg = """\
URL: %(url)s
Title: %(title)s
""" % {'url' : ext_ref.url,
       'title' : ext_ref.title}

    send_edit_notification_simple(
        ext_ref.bug,
        FROM_ADDR, get_cc_list(ext_ref.bug),
        '"%s" web link added' % ext_ref.bug.title, msg)

def notify_bug_watch_added(watch, event):
    """Notify CC'd list that a new watch has been added for this
    bug."""
    msg = """\
Bug Tracker: %(bug_tracker)s
Remote Bug: %(remote_bug)s
""" % {'bug_tracker' : watch.bugtracker.title, 'remote_bug' : watch.remotebug}

    send_edit_notification_simple(
        watch.bug,
        FROM_ADDR, get_cc_list(watch.bug),
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
        bug = event.object_before_modification.bug,
        from_addr = FROM_ADDR,
        to_addrs = get_cc_list(modified_bug_watch.bug),
        subject = '"%s" watch edited' % event.object_before_modification.bug.title,
        edit_header_line = (
            "Edited watch on bugtracker: %s" %
            event.object_before_modification.bugtracker.title),
        changes = changes)
