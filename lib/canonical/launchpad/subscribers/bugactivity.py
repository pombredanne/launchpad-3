from datetime import datetime

from zope.security.proxy import removeSecurityProxy
from zope.proxy import isProxy

from canonical.database.constants import nowUTC
from canonical.launchpad.database import Bug, BugActivity, Person

def what_changed(sqlobject_modified_event):
    before = sqlobject_modified_event.object_before_modification
    after = sqlobject_modified_event.object
    fields = sqlobject_modified_event.edited_fields
    changes = {}
    for f in fields:
        val_before = getattr(before, f, None)
        val_after = getattr(after, f, None)
        if isProxy(val_before):
            val_before = removeSecurityProxy(val_before)
        if isProxy(val_after):
            val_after = removeSecurityProxy(val_after)
        if isinstance(val_before, Person):
            val_before = val_before.name
        if isinstance(val_after, Person):
            val_after = val_after.name
        if val_before != val_after:
            changes[f] = [val_before, val_after]

    return changes

def record_bug_added(bug_add_form, object_created_event):
    bug = Bug.get(bug_add_form.id)
    BugActivity(
        bug = bug.id,
        datechanged = datetime.now(),
        person = int(bug.ownerID),
        whatchanged = "bug",
        message = "added bug")

def record_bug_edited(bug_edited, sqlobject_modified_event):
    changes = what_changed(sqlobject_modified_event)

    if changes:
        BugActivity(
            bug=bug_edited.id,
            datechanged=nowUTC,
            person=int(sqlobject_modified_event.principal.id),
            whatchanged=', '.join(changes.keys()),
            message='XXX: not yet implemented')

def record_package_assignment_added(package_assignment, object_created_event):
    BugActivity(
        bug=package_assignment.bugID,
        datechanged=nowUTC,
        person=int(package_assignment.ownerID),
        whatchanged='assigned to package ' + package_assignment.sourcepackage.sourcepackagename.name)

def record_package_assignment_edited(package_assignment_edited, sqlobject_modified_event):
    changes = what_changed(sqlobject_modified_event)
    if changes:
        package_name = package_assignment_edited.sourcepackage.sourcepackagename.name
        right_now = datetime.utcnow()
        for changed_field in changes.keys():
            BugActivity(
                bug=package_assignment_edited.bug.id,
                datechanged=right_now,
                person=int(sqlobject_modified_event.principal.id),
                whatchanged="%s: %s" % (package_name, changed_field),
                oldvalue=changes[changed_field][0],
                newvalue=changes[changed_field][1],
                message='XXX: not yet implemented')

def record_product_assignment_added(product_assignment, object_created_event):
    BugActivity(
        bug=product_assignment.bugID,
        datechanged=datetime.utcnow(),
        person=int(product_assignment.ownerID),
        whatchanged='assigned to product ' + product_assignment.product.fullname())

def record_product_assignment_edited(product_assignment_edited, sqlobject_modified_event):
    changes = what_changed(sqlobject_modified_event)
    if changes:
        product_name = product_assignment_edited.product.fullname()
        right_now = datetime.utcnow()
        for changed_field in changes.keys():
            BugActivity(
                bug=product_assignment_edited.bug.id,
                datechanged=right_now,
                person=int(sqlobject_modified_event.principal.id),
                whatchanged="%s: %s" % (product_name, changed_field),
                oldvalue=changes[changed_field][0],
                newvalue=changes[changed_field][1],
                message='XXX: not yet implemented')
