# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy
from zope.proxy import isProxy
from zope.schema.vocabulary import getVocabularyRegistry

from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces import (
    IBug, IBugActivitySet, IMilestone, IPerson, IProductRelease,
    ISourcePackageRelease)
from canonical.lazr import BaseItem

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
    elif IMilestone.providedBy(obj):
        return obj.name
    elif isinstance(obj, BaseItem):
        return obj.title
    elif isinstance(obj, basestring):
        return obj
    else:
        return None


def what_changed(sqlobject_modified_event):
    before = sqlobject_modified_event.object_before_modification
    after = sqlobject_modified_event.object
    fields = sqlobject_modified_event.edited_fields
    changes = {}
    for fieldname in fields:
        val_before = getattr(before, fieldname, None)
        val_after = getattr(after, fieldname, None)

        #XXX Bjorn Tillenius 2005-06-09: This shouldn't be necessary.
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
    getUtility(IBugActivitySet).new(
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
                if oldvalue is None and newvalue is not None:
                    whatchanged = 'marked as duplicate'
                elif oldvalue is not None and newvalue is not None:
                    whatchanged = 'changed duplicate marker'
                elif oldvalue is not None and newvalue is None:
                    whatchanged = 'removed duplicate marker'
            else:
                whatchanged = changed_field
            getUtility(IBugActivitySet).new(
                bug = bug_edited.id,
                datechanged = UTC_NOW,
                person = sqlobject_modified_event.user,
                whatchanged = whatchanged,
                oldvalue = oldvalue,
                newvalue = newvalue,
                message = "")

def record_bug_task_added(bug_task, object_created_event):
    getUtility(IBugActivitySet).new(
        bug=bug_task.bug,
        datechanged=UTC_NOW,
        person=object_created_event.user,
        whatchanged='bug',
        message='assigned to ' + bug_task.bugtargetname)

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
            getUtility(IBugActivitySet).new(
                bug=bug_task_edited.bug,
                datechanged=UTC_NOW,
                person=sqlobject_modified_event.user,
                whatchanged="%s: %s" % (task_title, changed_field),
                oldvalue=oldvalue,
                newvalue=newvalue)

def record_product_task_added(product_task, object_created_event):
    getUtility(IBugActivitySet).new(
        bug=product_task.bug,
        datechanged=UTC_NOW,
        person=object_created_event.user,
        whatchanged='bug',
        message='assigned to product ' + product_task.product.name)

def record_product_task_edited(product_task_edited, sqlobject_modified_event):
    changes = what_changed(sqlobject_modified_event)
    if changes:
        product = sqlobject_modified_event.object_before_modification.product
        for changed_field in changes.keys():
            oldvalue, newvalue = changes[changed_field]
            getUtility(IBugActivitySet).new(
                bug=product_task_edited.bug,
                datechanged=UTC_NOW,
                person=sqlobject_modified_event.user,
                whatchanged="%s: %s" % (product.name, changed_field),
                oldvalue=oldvalue,
                newvalue=newvalue)

def record_package_infestation_added(package_infestation, object_created_event):
    package_release_name = "%s %s" % (
        package_infestation.sourcepackagerelease.sourcepackagename.name,
        package_infestation.sourcepackagerelease.version)
    getUtility(IBugActivitySet).new(
        bug=package_infestation.bug,
        datechanged=UTC_NOW,
        person=package_infestation.creatorID,
        whatchanged="bug",
        message="added infestation of package release " + package_release_name)

def record_package_infestation_edited(package_infestation_edited,
                                      sqlobject_modified_event):
    changes = what_changed(sqlobject_modified_event)
    if changes:
        event = sqlobject_modified_event
        srcpkgrelease = event.object_before_modification.sourcepackagerelease
        package_release_name = "%s %s" % (
            srcpkgrelease.sourcepackagename.name, srcpkgrelease.version)
        for changed_field in changes.keys():
            oldvalue, newvalue = changes[changed_field]
            getUtility(IBugActivitySet).new(
                bug=package_infestation_edited.bug.id,
                datechanged=UTC_NOW,
                person=event.user,
                whatchanged="%s: %s" % (package_release_name, changed_field),
                oldvalue=oldvalue,
                newvalue=newvalue)

def record_product_infestation_added(product_infestation, object_created_event):
    product_release_name = "%s %s" % (
        product_infestation.productrelease.product.name,
        product_infestation.productrelease.version)
    getUtility(IBugActivitySet).new(
        bug=product_infestation.bug,
        datechanged=UTC_NOW,
        person=product_infestation.creatorID,
        whatchanged="bug",
        message="added infestation of product release " + product_release_name)

def record_product_infestation_edited(product_infestation_edited,
                                      sqlobject_modified_event):
    changes = what_changed(sqlobject_modified_event)
    if changes:
        event = sqlobject_modified_event
        productrelease = event.object_before_modification.productrelease
        product_release_name = "%s %s" % (productrelease.product.name,
                                          productrelease.version)
        for changed_field in changes.keys():
            oldvalue, newvalue = changes[changed_field]
            getUtility(IBugActivitySet).new(
                bug=product_infestation_edited.bug.id,
                datechanged=UTC_NOW,
                person=event.user,
                whatchanged="%s: %s" % (product_release_name, changed_field),
                oldvalue=oldvalue,
                newvalue=newvalue)


def record_bugsubscription_edited(bugsubscription_edited,
                                  sqlobject_modified_event):
    changes = what_changed(sqlobject_modified_event)
    if changes:
        for changed_field in changes.keys():
            oldvalue, newvalue = changes[changed_field]
            getUtility(IBugActivitySet).new(
                bug=bugsubscription_edited.bug,
                datechanged=UTC_NOW,
                person=sqlobject_modified_event.user,
                whatchanged="subscriber %s" % (
                    bugsubscription_edited.person.browsername),
                oldvalue=oldvalue,
                newvalue=newvalue)


def record_bug_attachment_added(attachment, created_event):
    """Record that an attachment was added."""
    getUtility(IBugActivitySet).new(
        bug=attachment.bug,
        datechanged=UTC_NOW,
        person=created_event.user,
        whatchanged='bug',
        message="added attachment '%s' (%s)" % (
            attachment.libraryfile.filename, attachment.title))


