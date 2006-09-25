# Copyright 2006 Canonical Ltd.  All rights reserved.

__all__ = [
    'serialise_bugtask'
    'export_bugtasks'
    ]

import base64
import cElementTree as ET

from zope.component import getUtility
from canonical.launchpad.interfaces import IBugTaskSet, BugTaskSearchParams
from canonical.launchpad.browser.bugtask import get_comments_for_bugtask

def addnode(parent, elementname, content, **attrs):
    node = ET.SubElement(parent, elementname, attrs)
    node.text = content
    node.tail = '\n'
    return node

def addperson(parent, elementname, person):
    return addnode(parent, elementname, person.displayname, name=person.name)

def serialise_bugtask(bugtask):
    bug = bugtask.bug
    bug_node = ET.Element('bug', id=str(bug.id))
    bug_node.text = bug_node.tail = '\n'

    if bug.duplicateof is not None:
        addnode(bug_node, 'duplicateof', None, bug=str(bug.duplicateof.id))
    addnode(bug_node, 'datecreated',
            bug.datecreated.strftime('%Y-%m-%dT%H:%M:%SZ'))
    if bug.name is not None:
        addnode(bug_node, 'nickname', bug.name)
    addnode(bug_node, 'title', bug.title)
    addnode(bug_node, 'description', bug.description)
    addperson(bug_node, 'reporter', bug.owner)

    # Information from bug task:
    addnode(bug_node, 'status', bugtask.status.name)
    addnode(bug_node, 'importance', bugtask.importance.name)
    if bugtask.milestone is not None:
        addnode(bug_node, 'milestone', bugtask.milestone.name)
    if bugtask.assignee is not None:
        addperson(bug_node, 'assignee', bugtask.assignee)

    if bug.tags:
        tags_node = ET.SubElement(bug_node, 'tags')
        tags_node.text = tags_node.tail = '\n'
        for tag in bug.tags:
            addnode(tags_node, 'tag', tag)
    
    subscribers = bug.getDirectSubscribers()
    if subscribers:
        subs_node = ET.SubElement(bug_node, 'subscriptions')
        subs_node.text = subs_node.tail = '\n'
        for person in subscribers:
            addperson(subs_node, 'subscriber', person)

    for comment in get_comments_for_bugtask(bugtask):
        comment_node = ET.SubElement(bug_node, 'comment')
        comment_node.text = comment_node.tail = '\n'
        addperson(comment_node, 'sender', comment.owner)
        addnode(comment_node, 'date',
                comment.datecreated.strftime('%Y-%m-%dT%H:%M:%SZ'))
        addnode(comment_node, 'text', comment.text_for_display)
        # Note that these are just references to the attachments
        # that are serialised after the comments.
        for attachment in comment.bugattachments:
            addnode(comment_node, 'attachment', None,
                    href=attachment.libraryfile.url)

    for attachment in bug.attachments:
        attachment_node = ET.SubElement(bug_node, 'attachment',
                                        href=attachment.libraryfile.url)
        attachment_node.text = attachment_node.tail = '\n'
        addnode(attachment_node, 'type', attachment.type.name)
        addnode(attachment_node, 'title', attachment.title)
        addnode(attachment_node, 'mimetype', attachment.libraryfile.mimetype)
        # Attach the attachment file contents, base 64 encoded.
        addnode(attachment_node, 'contents',
                base64.encodestring(attachment.libraryfile.read()))

    return bug_node


def export_bugtasks(ztm, bugtarget, output):
    # Collect bug task IDs.
    # XXX 2006-09-25 jamesh
    # This will only get the IDs of public bugs.  We probably want to
    # be able to do a separate private bugs dump.
    ids = [task.id for task in bugtarget.searchTasks(
        BugTaskSearchParams(user=None, omit_dupes=False, orderby='id'))]
    bugtaskset = getUtility(IBugTaskSet)
    output.write('<launchpad-bugs>\n')
    for count, taskid in enumerate(ids):
        task = bugtaskset.get(taskid)
        tree = ET.ElementTree(serialise_bugtask(task))
        tree.write(output)
        # Periodically abort the transaction so that we don't lock
        # everyone else out.
        if count % 100:
            ztm.abort()
    output.write('</launchpad-bugs>\n')
