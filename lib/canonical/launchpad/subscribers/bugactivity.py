# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from datetime import datetime

from zope.security.proxy import removeSecurityProxy
from zope.proxy import isProxy
from zope.schema.vocabulary import getVocabularyRegistry

from canonical.lp.dbschema import Item
from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces import (
    IPerson, IBug, ISourcePackageRelease, IProductRelease)
from canonical.launchpad.database import BugActivity

vocabulary_registry = getVocabularyRegistry()


def get_string_representation(obj):
    """Returns a string representation of an object.

    It can be used as oldvalue and newvalue.

    Returns None if no representation can be made.
    """
    if IPerson.providedBy(obj):
        return obj.name
    if IBug.providedBy(obj):
        return str(obj.id)
    elif ISourcePackageRelease.providedBy(obj):
        return "%s %s" % (obj.sourcepackagename.name, obj.version)
    elif IProductRelease.providedBy(obj):
        return "%s %s" % (obj.product.name, obj.version)
    elif isinstance(obj, Item):
        return obj.title
    elif isinstance(obj, basestring):
        return obj

    return None
    

def what_changed(sqlobject_modified_event):
    before = sqlobject_modified_event.object_before_modification
    after = sqlobject_modified_event.object
    fields = sqlobject_modified_event.edited_fields
    changes = {}
    for fieldname in fields:
        val_before = getattr(before, fieldname, None)
        val_after = getattr(after, fieldname, None)

        #XXX: This shouldn't be necessary -- Bjorn Tillenius, 2005-06-09
        # peel off the zope stuff
        if isProxy(val_before):
            val_before = removeSecurityProxy(val_before)
        if isProxy(val_after):
            val_after = removeSecurityProxy(val_after)

        before_string = get_string_representation(val_before)
        after_string = get_string_representation(val_after)

        if before_string != after_string:
            changes[fieldname] = [before_string, after_string]

    return changes

def record_bug_added(bug, object_created_event):
    BugActivity(
        bug = bug.id,
        datechanged = UTC_NOW,
        person = object_created_event.user,
        whatchanged = "bug",
        message = "added bug")

def record_bug_edited(bug_edited, sqlobject_modified_event):
    changes = what_changed(sqlobject_modified_event)

    if changes:
        for changed_field in changes.keys():
            oldvalue, newvalue = changes[changed_field]
            if changed_field == 'duplicateof':
                whatchanged = 'marked as duplicate'
            else:
                whatchanged = changed_field
            BugActivity(
                bug = bug_edited.id,
                datechanged = UTC_NOW,
                person = sqlobject_modified_event.user,
                whatchanged = whatchanged,
                oldvalue = oldvalue,
                newvalue = newvalue,
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
        person=object_created_event.user,
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
                bug=bug_task_edited.bug,
                datechanged=UTC_NOW,
                person=sqlobject_modified_event.user,
                whatchanged="%s: %s" % (task_title, changed_field),
                oldvalue=oldvalue,
                newvalue=newvalue,
                message='XXX: not yet implemented')

def record_product_task_added(product_task, object_created_event):
    BugActivity(
        bug=product_task.bugID,
        datechanged=UTC_NOW,
        person=object_created_event.user,
        whatchanged='bug',
        message='assigned to product ' + product_task.product.name)

def record_product_task_edited(product_task_edited, sqlobject_modified_event):
    changes = what_changed(sqlobject_modified_event)
    if changes:
        product_name = sqlobject_modified_event.object_before_modification.product.name
        for changed_field in changes.keys():
            oldvalue, newvalue = changes[changed_field]
            BugActivity(
                bug=product_task_edited.bug,
                datechanged=UTC_NOW,
                person=sqlobject_modified_event.user,
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
                person=sqlobject_modified_event.user,
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
                person=sqlobject_modified_event.user,
                whatchanged="%s: %s" % (product_release_name, changed_field),
                oldvalue=oldvalue,
                newvalue=newvalue,
                message='XXX: not yet implemented')

def record_bugsubscription_added(bugsubscription_added, object_created_event):
    sv = vocabulary_registry.get(None, "Subscription")
    term = sv.getTerm(bugsubscription_added.subscription)
    BugActivity(
        bug=bugsubscription_added.bug,
        datechanged=UTC_NOW,
        person=object_created_event.user,
        whatchanged='bug',
        message='added subscriber %s (%s)' % (
            bugsubscription_added.person.browsername, term.token))

def record_bugsubscription_edited(bugsubscription_edited,
                                  sqlobject_modified_event):
    changes = what_changed(sqlobject_modified_event)
    if changes:
        for changed_field in changes.keys():
            oldvalue, newvalue = changes[changed_field]
            BugActivity(
                bug=bugsubscription_edited.bug,
                datechanged=UTC_NOW,
                person=sqlobject_modified_event.user,
                whatchanged="subscriber %s" % (
                    bugsubscription_edited.person.browsername),
                oldvalue=oldvalue,
                newvalue=newvalue)


