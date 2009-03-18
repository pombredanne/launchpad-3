# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy
from zope.proxy import isProxy
from zope.schema.vocabulary import getVocabularyRegistry
from lazr.enum import BaseItem

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import block_implicit_flushes
from canonical.launchpad.interfaces import (
    IBug, IBugActivitySet, IMilestone, IPerson, IProductRelease,
    ISourcePackageRelease)

vocabulary_registry = getVocabularyRegistry()


BUG_INTERESTING_FIELDS = [
    'duplicateof',
    'name',
    'private',
    'security_related',
    'tags',
    ]


BUGTASK_INTERESTING_FIELDS = [
    'assignee',
    'bugwatch',
    'importance',
    'milestone',
    'status',
    'target',
    ]


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
    elif isinstance(obj, bool):
        return str(obj)
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


@block_implicit_flushes
def record_bug_added(bug, object_created_event):
    getUtility(IBugActivitySet).new(
        bug = bug.id,
        datechanged = UTC_NOW,
        person = IPerson(object_created_event.user),
        whatchanged = "bug",
        message = "added bug")


@block_implicit_flushes
def record_bug_edited(bug_edited, sqlobject_modified_event):
    # If the event was triggered by a web service named operation, its
    # edited_fields will be empty. We'll need to check all interesting
    # fields to see which were actually changed.
    sqlobject_modified_event.edited_fields = BUG_INTERESTING_FIELDS

    changes = what_changed(sqlobject_modified_event)
    for changed_field in changes:
        oldvalue, newvalue = changes[changed_field]
        if changed_field == 'duplicateof':
            if oldvalue is None and newvalue is not None:
                whatchanged = 'marked as duplicate'
            elif oldvalue is not None and newvalue is not None:
                whatchanged = 'changed duplicate marker'
            elif oldvalue is not None and newvalue is None:
                whatchanged = 'removed duplicate marker'
        elif changed_field == 'private':
            whatchanged = 'privacy'
            privacy_values = {'True': 'private', 'False': 'public'}
            oldvalue = privacy_values[oldvalue]
            newvalue = privacy_values[newvalue]
        elif changed_field == 'security_related':
            whatchanged = 'security'
            security_values = {
                'True': 'security vulnerability',
                'False': 'not security vulnerability',
                }
            oldvalue = security_values[oldvalue]
            newvalue = security_values[newvalue]
        else:
            whatchanged = changed_field

        getUtility(IBugActivitySet).new(
            bug=bug_edited.id,
            datechanged=UTC_NOW,
            person=IPerson(sqlobject_modified_event.user),
            whatchanged=whatchanged,
            oldvalue=oldvalue,
            newvalue=newvalue,
            message="")


@block_implicit_flushes
def record_bug_task_added(bug_task, object_created_event):
    getUtility(IBugActivitySet).new(
        bug=bug_task.bug,
        datechanged=UTC_NOW,
        person=IPerson(object_created_event.user),
        whatchanged='bug',
        message='assigned to ' + bug_task.bugtargetname)


@block_implicit_flushes
def record_bug_task_edited(bug_task_edited, sqlobject_modified_event):
    """Make an activity note that a bug task was edited."""
    # If the event was triggered by a web service named operation, its
    # edited_fields will be empty. We'll need to check all fields to
   # see which were actually changed.
    sqlobject_modified_event.edited_fields = BUGTASK_INTERESTING_FIELDS
    changes = what_changed(sqlobject_modified_event)
    if changes:
        task_title = ""
        bug_task_before = sqlobject_modified_event.object_before_modification
        if bug_task_edited.product:
            if bug_task_before.product is None:
                task_title = None
            else:
                task_title = bug_task_before.bugtargetname
        else:
            if bug_task_before.sourcepackagename is None:
                task_title = None
            else:
                task_title = bug_task_before.bugtargetname
        for changed_field in changes.keys():
            oldvalue, newvalue = changes[changed_field]
            if oldvalue is not None:
                oldvalue = unicode(oldvalue)
            if newvalue is not None:
                newvalue = unicode(newvalue)
            getUtility(IBugActivitySet).new(
                bug=bug_task_edited.bug,
                datechanged=UTC_NOW,
                person=IPerson(sqlobject_modified_event.user),
                whatchanged="%s: %s" % (task_title, changed_field),
                oldvalue=oldvalue,
                newvalue=newvalue)


@block_implicit_flushes
def record_product_task_added(product_task, object_created_event):
    getUtility(IBugActivitySet).new(
        bug=product_task.bug,
        datechanged=UTC_NOW,
        person=IPerson(object_created_event.user),
        whatchanged='bug',
        message='assigned to product ' + product_task.product.name)


@block_implicit_flushes
def record_product_task_edited(product_task_edited, sqlobject_modified_event):
    # If the event was triggered by a web service named operation, its
    # edited_fields will be empty. We'll need to check all fields to
    # see which were actually changed.
    sqlobject_modified_event.edited_fields = BUGTASK_INTERESTING_FIELDS
    changes = what_changed(sqlobject_modified_event)
    if changes:
        product = sqlobject_modified_event.object_before_modification.product
        for changed_field in changes.keys():
            oldvalue, newvalue = changes[changed_field]
            getUtility(IBugActivitySet).new(
                bug=product_task_edited.bug,
                datechanged=UTC_NOW,
                person=IPerson(sqlobject_modified_event.user),
                whatchanged="%s: %s" % (product.name, changed_field),
                oldvalue=oldvalue,
                newvalue=newvalue)


@block_implicit_flushes
def record_bugsubscription_added(bugsubscription_added, object_created_event):
    getUtility(IBugActivitySet).new(
        bug=bugsubscription_added.bug,
        datechanged=UTC_NOW,
        person=IPerson(object_created_event.user),
        whatchanged='bug',
        message='added subscriber %s' % (
            bugsubscription_added.person.browsername))


@block_implicit_flushes
def record_bugsubscription_edited(bugsubscription_edited,
                                  sqlobject_modified_event):
    changes = what_changed(sqlobject_modified_event)
    if changes:
        for changed_field in changes.keys():
            oldvalue, newvalue = changes[changed_field]
            getUtility(IBugActivitySet).new(
                bug=bugsubscription_edited.bug,
                datechanged=UTC_NOW,
                person=IPerson(sqlobject_modified_event.user),
                whatchanged="subscriber %s" % (
                    bugsubscription_edited.person.browsername),
                oldvalue=oldvalue,
                newvalue=newvalue)


@block_implicit_flushes
def record_bug_attachment_added(attachment, created_event):
    """Record that an attachment was added."""
    getUtility(IBugActivitySet).new(
        bug=attachment.bug,
        datechanged=UTC_NOW,
        person=IPerson(created_event.user),
        whatchanged='bug',
        message="added attachment '%s' (%s)" % (
            attachment.libraryfile.filename, attachment.title))
