from datetime import datetime

from zope.security.proxy import removeSecurityProxy
from zope.proxy import isProxy
from zope.schema.vocabulary import getVocabularyRegistry

from canonical.lp.dbschema import BugTaskStatus, BugSeverity, BugPriority, BugInfestationStatus
from canonical.database.constants import UTC_NOW
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
            val_before = val_before.title
        elif f == 'priority':
            val_before = val_before.title
        elif f == 'severity':
            val_before = val_before.title
        elif f == 'infestationstatus':
            val_before = val_before.title
        elif isinstance(val_before, Person):
            val_before = val_before.name
        elif isinstance(val_before, SourcePackageRelease):
            val_before = "%s %s" % (
                val_before.sourcepackagename.name,
                val_before.version)
        elif isinstance(val_before, ProductRelease):
            val_before = "%s %s" % (
                val_before.product.name,
                val_before.version)

        # figure out the new value
        if f == 'status':
            val_after = val_after.title
        elif f == 'priority':
            val_after = val_after.title
        elif f == 'severity':
            val_after = val_after.title
        elif f == 'infestationstatus':
            val_after = val_after.title
        elif isinstance(val_after, Person):
                    val_after = val_after.name
        elif isinstance(val_after, SourcePackageRelease):
            val_after = "%s %s" % (
                val_after.sourcepackagename.name,
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
        datechanged = UTC_NOW,
        person = int(bug.ownerID),
        whatchanged = "bug",
        message = "added bug")

def record_bug_edited(bug_edited, sqlobject_modified_event):
    changes = what_changed(sqlobject_modified_event)

    if changes:
        duplicateof_change = changes.pop("duplicateof", None)

        for changed_field in changes.keys():
            oldvalue, newvalue = changes[changed_field]
            BugActivity(
                bug = bug_edited.id,
                datechanged = nowUTC,
                person = int(sqlobject_modified_event.principal.id),
                whatchanged = changed_field,
                oldvalue = oldvalue,
                newvalue = newvalue,
                message = "")

        if duplicateof_change is not None:
            olddup, newdup = duplicateof_change
            # special-case duplicateof because the values are objects,
            # rather than IDs, so we need to .id the values explicitly
            oldid = None
            newid = None
            if olddup is not None:
                oldid = olddup.id
            if newdup is not None:
                newid = newdup.id

            BugActivity(
                bug = sqlobject_modified_event.object_before_modification.id,
                datechanged = nowUTC,
                person = int(sqlobject_modified_event.principal.id),
                whatchanged = "marked as duplicate",
                oldvalue = oldid,
                newvalue = newid,
                message = "")

def record_bug_task_added(bug_task, object_created_event):
    activity_message = ""
    if bug_task.product:
        activity_message = 'assigned to upstream ' + bug_task.product.name
    else:
        activity_message = 'assigned to source package ' + bug_task.sourcepackagename.name
    BugActivity(
        bug=bug_task.bugID,
        datechanged=UTC_NOW,
        person=int(bug_task.ownerID),
        whatchanged='bug',
        message=activity_message)

def record_bug_task_edited(bug_task_edited, sqlobject_modified_event):
    """Make an activity note that a bug task was edited."""
    changes = what_changed(sqlobject_modified_event)
    if changes:
        task_title = ""
        obm = sqlobject_modified_event.object_before_modification
        if bug_task_edited.product:
            if obm.product is None:
                task_title = None
            else:
                task_title = obm.product.name
        else:
            if obm.sourcepackagename is None:
                task_title = None
            else:
                task_title = obm.sourcepackagename.name
        for changed_field in changes.keys():
            oldvalue, newvalue = changes[changed_field]
            if oldvalue is not None:
                oldvalue = unicode(oldvalue)
            if newvalue is not None:
                newvalue = unicode(newvalue)
            BugActivity(
                bug=bug_task_edited.bug.id,
                datechanged=UTC_NOW,
                person=int(sqlobject_modified_event.principal.id),
                whatchanged="%s: %s" % (task_title, changed_field),
                oldvalue=oldvalue,
                newvalue=newvalue,
                message='XXX: not yet implemented')

def record_product_task_added(product_task, object_created_event):
    BugActivity(
        bug=product_task.bugID,
        datechanged=UTC_NOW,
        person=int(product_task.ownerID),
        whatchanged='bug',
        message='assigned to product ' + product_task.product.name)

def record_product_task_edited(product_task_edited, sqlobject_modified_event):
    changes = what_changed(sqlobject_modified_event)
    if changes:
        product_name = sqlobject_modified_event.object_before_modification.product.name
        for changed_field in changes.keys():
            oldvalue, newvalue = changes[changed_field]
            BugActivity(
                bug=product_task_edited.bug.id,
                datechanged=UTC_NOW,
                person=int(sqlobject_modified_event.principal.id),
                whatchanged="%s: %s" % (product_name, changed_field),
                oldvalue=oldvalue,
                newvalue=newvalue,
                message='XXX: not yet implemented')

def record_package_infestation_added(package_infestation, object_created_event):
    package_release_name = "%s %s" % (
        package_infestation.sourcepackagerelease.sourcepackagename.name,
        package_infestation.sourcepackagerelease.version)
    BugActivity(
        bug=package_infestation.bugID,
        datechanged=UTC_NOW,
        person=package_infestation.creatorID,
        whatchanged="bug",
        message="added infestation of package release " + package_release_name)

def record_package_infestation_edited(package_infestation_edited, sqlobject_modified_event):
    changes = what_changed(sqlobject_modified_event)
    if changes:
        package_release_name = "%s %s" % (
            sqlobject_modified_event.object_before_modification.sourcepackagerelease.sourcepackagename.name,
            sqlobject_modified_event.object_before_modification.sourcepackagerelease.version)
        for changed_field in changes.keys():
            oldvalue, newvalue = changes[changed_field]
            BugActivity(
                bug=package_infestation_edited.bug.id,
                datechanged=UTC_NOW,
                person=int(sqlobject_modified_event.principal.id),
                whatchanged="%s: %s" % (package_release_name, changed_field),
                oldvalue=oldvalue,
                newvalue=newvalue,
                message='XXX: not yet implemented')

def record_product_infestation_added(product_infestation, object_created_event):
    product_release_name = "%s %s" % (
        product_infestation.productrelease.product.name,
        product_infestation.productrelease.version)
    BugActivity(
        bug=product_infestation.bugID,
        datechanged=UTC_NOW,
        person=product_infestation.creatorID,
        whatchanged="bug",
        message="added infestation of product release " + product_release_name)

def record_product_infestation_edited(product_infestation_edited, sqlobject_modified_event):
    changes = what_changed(sqlobject_modified_event)
    if changes:
        product_release_name = "%s %s" % (
            sqlobject_modified_event.object_before_modification.productrelease.product.name,
            sqlobject_modified_event.object_before_modification.productrelease.version)
        for changed_field in changes.keys():
            oldvalue, newvalue = changes[changed_field]
            BugActivity(
                bug=product_infestation_edited.bug.id,
                datechanged=UTC_NOW,
                person=int(sqlobject_modified_event.principal.id),
                whatchanged="%s: %s" % (product_release_name, changed_field),
                oldvalue=oldvalue,
                newvalue=newvalue,
                message='XXX: not yet implemented')

def record_bugwatch_added(bugwatch_added, object_created_event):
    sv = vocabulary_registry.get(None, "Subscription")
    term = sv.getTerm(bugwatch_added.subscription)
    BugActivity(
        bug=bugwatch_added.bug.id,
        datechanged=UTC_NOW,
        person=bugwatch_added.personID,
        whatchanged='add subscriber %s (%s)' % (
            bugwatch_added.person.displayname, term.token))

def record_bugwatch_edited(bugwatch_edited, sqlobject_modified_event):
    changes = what_changed(sqlobject_modified_event)
    if changes:
        oldvalue, newvalue = changes[changed_field]
        for changed_field in changes.keys():
            BugActivity(
                bug=bugwatch_edited.bug.id,
                datechanged=UTC_NOW,
                person=sqlobject_modified_event.principal.id,
                whatchanged="subscriber %s" % (
                    bugwatch_edited.person.displayname),
                oldvalue=oldvalue,
                newvalue=newvalue)


