from datetime import datetime

from zope.security.proxy import removeSecurityProxy
from zope.proxy import isProxy
from zope.schema.vocabulary import getVocabularyRegistry

from canonical.lp.dbschema import BugTaskStatus, BugSeverity, BugPriority, BugInfestationStatus
from canonical.database.constants import nowUTC
from canonical.launchpad.database import Bug, BugActivity, Person, SourcePackageRelease, ProductRelease

vocabulary_registry = getVocabularyRegistry()

def what_changed(sqlobject_modified_event):
    before = sqlobject_modified_event.object_before_modification
    after = sqlobject_modified_event.object
    fields = sqlobject_modified_event.edited_fields
    changes = {}
    for f in fields:
        val_before = getattr(before, f, None)
        val_after = getattr(after, f, None)

        # peel off the zope stuff
        if isProxy(val_before):
            val_before = removeSecurityProxy(val_before)
        if isProxy(val_after):
            val_after = removeSecurityProxy(val_after)

        # figure out the orig value
        if f == 'status':
            val_before = BugTaskStatus.items[val_before].title
        elif f == 'priority':
            val_before = BugPriority.items[val_before].title
        elif f == 'severity':
            val_before = BugSeverity.items[val_before].title
        elif f == 'infestationstatus':
            val_before = BugInfestationStatus.items[val_before].title
        elif isinstance(val_before, Person):
            val_before = val_before.name
        elif isinstance(val_before, SourcePackageRelease):
            val_before = "%s %s" % (
                val_before.sourcepackage.sourcepackagename.name,
                val_before.version)
        elif isinstance(val_before, ProductRelease):
            val_before = "%s %s" % (
                val_before.product.name,
                val_before.version)

        # figure out the new value
        if f == 'status':
            val_after = BugTaskStatus.items[val_after].title
        elif f == 'priority':
            val_after = BugPriority.items[val_after].title
        elif f == 'severity':
            val_after = BugSeverity.items[val_after].title
        elif f == 'infestationstatus':
            val_after = BugInfestationStatus.items[val_after].title
        elif isinstance(val_after, Person):
                    val_after = val_after.name
        elif isinstance(val_after, SourcePackageRelease):
            val_after = "%s %s" % (
                val_after.sourcepackage.sourcepackagename.name,
                val_after.version)
        elif isinstance(val_after, ProductRelease):
            val_after = "%s %s" % (
                val_after.product.name,
                val_after.version)

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
        for changed_field in changes.keys():
            BugActivity(
                bug=sqlobject_modified_event.object_before_modification.id,
                datechanged=nowUTC,
                person=int(sqlobject_modified_event.principal.id),
                whatchanged=changed_field,
                oldvalue=changes[changed_field][0],
                newvalue=changes[changed_field][1],
                message='XXX: not yet implemented')

def record_bug_task_added(bug_task, object_created_event):
    activity_message = ""
    if bug_task.product:
        activity_message = 'assigned to upstream ' + bug_task.product.name
    else:
        activity_message = 'assigned to source package ' + bug_task.sourcepackagename.name
    BugActivity(
        bug=bug_task.bugID,
        datechanged=nowUTC,
        person=int(bug_task.ownerID),
        whatchanged='bug',
        message=activity_message)

def record_bug_task_edited(bug_task_edited, sqlobject_modified_event):
    changes = what_changed(sqlobject_modified_event)
    if changes:
        assignment_title = ""
        obm = sqlobject_modified_event.object_before_modification
        if bug_task_edited.product:
            if obm.product is None:
                assignment_title = None
            else:
                assignment_title = obm.product.name
        else:
            if obm.sourcepackagename is None:
                assignment_title = None
            else:
                assignment_title = obm.sourcepackagename.name
        right_now = datetime.utcnow()
        for changed_field in changes.keys():
            ov = changes[changed_field][0]
            if ov is not None:
                ov = unicode(ov)
            nv = changes[changed_field][1]
            if nv is not None:
                nv = unicode(nv)
            BugActivity(
                bug=bug_task_edited.bug.id,
                datechanged=right_now,
                person=int(sqlobject_modified_event.principal.id),
                whatchanged="%s: %s" % (assignment_title, changed_field),
                oldvalue=ov,
                newvalue=nv,
                message='XXX: not yet implemented')

def record_product_assignment_added(product_assignment, object_created_event):
    BugActivity(
        bug=product_assignment.bugID,
        datechanged=datetime.utcnow(),
        person=int(product_assignment.ownerID),
        whatchanged='bug',
        message='assigned to product ' + product_assignment.product.name)

def record_product_assignment_edited(product_assignment_edited, sqlobject_modified_event):
    changes = what_changed(sqlobject_modified_event)
    if changes:
        product_name = sqlobject_modified_event.object_before_modification.product.name
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

def record_package_infestation_added(package_infestation, object_created_event):
    package_release_name = "%s %s" % (
        package_infestation.sourcepackagerelease.sourcepackage.sourcepackagename.name,
        package_infestation.sourcepackagerelease.version)
    BugActivity(
        bug=package_infestation.bugID,
        datechanged=datetime.utcnow(),
        person=package_infestation.creatorID,
        whatchanged="bug",
        message="added infestation of package release " + package_release_name)

def record_package_infestation_edited(package_infestation_edited, sqlobject_modified_event):
    changes = what_changed(sqlobject_modified_event)
    if changes:
        package_release_name = "%s %s" % (
            sqlobject_modified_event.object_before_modification.sourcepackagerelease.sourcepackage.sourcepackagename.name,
            sqlobject_modified_event.object_before_modification.sourcepackagerelease.version)
        right_now = datetime.utcnow()
        for changed_field in changes.keys():
            BugActivity(
                bug=package_infestation_edited.bug.id,
                datechanged=right_now,
                person=int(sqlobject_modified_event.principal.id),
                whatchanged="%s: %s" % (package_release_name, changed_field),
                oldvalue=changes[changed_field][0],
                newvalue=changes[changed_field][1],
                message='XXX: not yet implemented')

def record_product_infestation_added(product_infestation, object_created_event):
    product_release_name = "%s %s" % (
        product_infestation.productrelease.product.name,
        product_infestation.productrelease.version)
    BugActivity(
        bug=product_infestation.bugID,
        datechanged=datetime.utcnow(),
        person=product_infestation.creatorID,
        whatchanged="bug",
        message="added infestation of product release " + product_release_name)

def record_product_infestation_edited(product_infestation_edited, sqlobject_modified_event):
    changes = what_changed(sqlobject_modified_event)
    if changes:
        product_release_name = "%s %s" % (
            sqlobject_modified_event.object_before_modification.productrelease.product.name,
            sqlobject_modified_event.object_before_modification.productrelease.version)
        right_now = datetime.utcnow()
        for changed_field in changes.keys():
            BugActivity(
                bug=product_infestation_edited.bug.id,
                datechanged=right_now,
                person=int(sqlobject_modified_event.principal.id),
                whatchanged="%s: %s" % (product_release_name, changed_field),
                oldvalue=changes[changed_field][0],
                newvalue=changes[changed_field][1],
                message='XXX: not yet implemented')

def record_bugwatch_added(bugwatch_added, object_created_event):
    sv = vocabulary_registry.get(None, "Subscription")
    term = sv.getTerm(bugwatch_added.subscription)
    BugActivity(
        bug=bugwatch_added.bug.id,
        datechanged=datetime.utcnow(),
        person=bugwatch_added.personID,
        whatchanged='add subscriber %s (%s)' % (
            bugwatch_added.person.displayname, term.token))

def record_bugwatch_edited(bugwatch_edited, sqlobject_modified_event):
    changes = what_changed(sqlobject_modified_event)
    if changes:
        right_now = datetime.utcnow()
        for changed_field in changes.keys():
            BugActivity(
                bug=sqlobject_modified_event.object_before_modification.bug.id,
                datechanged=right_now,
                person=sqlobject_modified_event.principal.id,
                whatchanged="subscriber %s" % (
                    sqlobject_modified_event.object_before_modification.person.displayname),
                oldvalue=changes[changed_field][0],
                newvalue=changes[changed_field][1])
                

