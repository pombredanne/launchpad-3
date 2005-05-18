# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Event handlers that send email notifications."""

__metaclass__ = type

import itertools
from textwrap import wrap

from zope.app import zapi
from zope.app.mail.interfaces import IMailDelivery
from zope.component import getUtility

from canonical.launchpad.interfaces import IBug, IBugSet, ITeam, IPerson, \
    IUpstreamBugTask, IDistroBugTask
from canonical.launchpad.mail import simple_sendmail
from canonical.launchpad.database import Bug, BugTracker, EmailAddress, \
     BugDelta, BugTaskDelta
from canonical.lp.dbschema import BugTaskStatus, BugPriority, \
     BugSeverity, BugInfestationStatus, BugExternalReferenceType, \
     BugSubscription
from canonical.launchpad.vocabularies import BugTrackerVocabulary

FROM_ADDR = "Malone Bugtracker <noreply@canonical.com>"
GLOBAL_NOTIFICATION_EMAIL_ADDRS = ("dilys@muse.19inch.net",)
CC = "CC"

def generate_bug_edit_email(bug_delta):
    """Generate a bug edit notification based on the bug_delta.

    bug_delta is an object that provides IBugDelta. The return value
    is (subject, body).
    """
    subject = "[Bug %d] %s" % (bug_delta.bug.id, bug_delta.bug.title)

    body = """\
%(browsername)s <%(email)s> made changes to:

    %(bugurl)s

""" % {'browsername' : bug_delta.user.browsername,
       'email' : bug_delta.user.preferredemail.email,
       'bugurl' : bug_delta.bugurl}

    # figure out what's been changed; add that information to the
    # email as appropriate
    if bug_delta.title is not None:
        body += "    - Changed title to:\n"
        body += "        %s\n" % bug_delta.title
    if bug_delta.summary is not None:
        body += "    - Changed summary to:\n"
        body += "\n".join(wrap(
            bug_delta.summary, width = 72,
            initial_indent = u"        ",
            subsequent_indent = u"        "))
        body += "\n"
    if bug_delta.description is not None:
        body += "    - Changed description to:\n"
        body += "\n".join(wrap(
            bug_delta.description, width = 72,
            initial_indent = u"        ",
            subsequent_indent = u"        "))
        body += "\n"
    for fieldname in ("private", "name"):
        changed_attr = getattr(bug_delta, fieldname)
        if changed_attr is not None:
            body += "    - Changed %s:\n" % fieldname
            body += "        %(old)s => %(new)s\n" % {
                'old' : changed_attr['old'],
                'new' : changed_attr['new']}
    if bug_delta.external_reference is not None:
        body += "    - Changed web links:\n"
        body += "        Added: %s (%s)\n" % (
            bug_delta.external_reference['new'].url,
            bug_delta.external_reference['new'].title)
        old_ext_ref = bug_delta.external_reference.get('old')
        if old_ext_ref is not None:
            body += "      Removed: %s (%s)\n" % (
                old_ext_ref.url, old_ext_ref.title)
    if bug_delta.bugwatch is not None:
        body += "    - Changed bug watches:\n"
        body += "        Added: Bug %s [%s]\n" % (
            bug_delta.bugwatch['new'].remotebug,
            bug_delta.bugwatch['new'].bugtracker.title)
        old_bug_watch = bug_delta.bugwatch.get('old')
        if old_bug_watch:
            body += "      Removed: Bug %s [%s]\n" % (
                old_bug_watch.remotebug,
                old_bug_watch.bugtracker.title)

    if bug_delta.cveref is not None:
        body += "    - Changed CVE references:\n"
        body += "        Added: %s [%s]\n" % (
            bug_delta.cveref['new'].cveref, bug_delta.cveref['new'].title)
        old_cveref = bug_delta.cveref.get('old')
        if old_cveref:
            body += "      Removed: %s [%s]\n" % (
                old_cveref.cveref, old_cveref.title)

    if bug_delta.bugtask_deltas is not None:
        bugtask_deltas = bug_delta.bugtask_deltas
        if not isinstance(bugtask_deltas, (list, tuple)):
            bugtask_deltas = [bugtask_deltas]
        for bugtask_delta in bugtask_deltas:
            if not body[-2:] == "\n\n":
                body += "\n"

            what = None
            where = None
            if IUpstreamBugTask.providedBy(bugtask_delta.bugtask):
                body += "Task: Upstream %s\n" % (
                    bugtask_delta.bugtask.product.displayname)
            elif IDistroBugTask.providedBy(bugtask_delta.bugtask):
                distroname = bugtask_delta.bugtask.distribution.name
                spname = None
                if (bugtask_delta.sourcepackagename is not None and
                    bugtask_delta.sourcepackagename.get("old") is not None):
                    spname = bugtask_delta.sourcepackagename["old"].name
                else:
                    if bugtask_delta.bugtask.sourcepackagename is not None:
                        spname = bugtask_delta.bugtask.sourcepackagename.name

                if spname:
                    body += "Task: %s %s\n" % (distroname, spname)
                else:
                    body += "Task: %s\n" % distroname
            else:
                raise ValueError(
                    "BugTask of unknown type: %s. Must provide either "
                    "IUpstreamBugTask or IDistroBugTask." % str(bugtask))

            for fieldname, displayattrname in (
                ("product", "displayname"),
                ("sourcepackagename", "name"),
                ("binarypackagename", "name"),
                ("status", "title"),
                ("target", "name"),
                ("priority", "title"),
                ("severity", "title")):
                change = getattr(bugtask_delta, fieldname)
                if change:
                    oldval_display = None
                    newval_display = None
                    if displayattrname is not None:
                        if change.get('old') is not None:
                            oldval_display = getattr(change['old'], displayattrname)
                        if change.get('new') is not None:
                            newval_display = getattr(change['new'], displayattrname)
                    else:
                        oldval_display = change.get('old')
                        newval_display = change.get('new')

                    changerow = (
                        "%(label)13s: %(oldval)s => %(newval)s\n" % {
                        'label' : fieldname, 'oldval' : oldval_display,
                        'newval' : newval_display})
                    body += changerow

            if bugtask_delta.assignee is not None:
                oldval_display = "(unassigned)"
                newval_display = "(unassigned)"
                if bugtask_delta.assignee.get('old'):
                    oldval_display = bugtask_delta.assignee['old'].browsername
                if bugtask_delta.assignee.get('new'):
                    newval_display = bugtask_delta.assignee['new'].browsername

                changerow = (
                    "%(label)13s: %(oldval)s => %(newval)s\n" % {
                    'label' : "assignee", 'oldval' : oldval_display,
                    'newval' : newval_display})
                body += changerow

    return (subject, body)


def send_bug_edit_notification(from_addr, to_addrs, bug_delta):
    """Send a notification email about a bug that was modified.

    The email is sent from from_addr to to_addrs with subject.
    bugdelta is an IBugDelta. A ValueError is raised if IBugDelta is
    None.
    """
    if bug_delta is None:
        raise ValueError("Can't send edit notification for empty bugdelta.")

    subject, body = generate_bug_edit_email(bug_delta)

    simple_sendmail(from_addr, to_addrs, subject, body)


def get_cc_list(bug):
    """Return the list of people that are CC'd on this bug."""
    subscriptions = []
    if not bug.private:
        subscriptions = list(GLOBAL_NOTIFICATION_EMAIL_ADDRS)

    subscriptions += bug.notificationRecipientAddresses()

    return subscriptions


# XXX: Brad Bollenbach, 2005-04-11: This function will probably be
# supplanted by get_bug_delta and get_task_delta (see slightly further
# down.)
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


def get_bug_delta(old_bug, new_bug, user, request):
    """Compute the delta from old_bug to new_bug.

    old_bug and new_bug are IBug's. user is an IPerson. Returns an
    IBugDelta if there are changes, or None if there were no changes.
    """
    changes = {}
    for field_name in ("title", "summary", "description"):
        # fields for which we simply show the new value when they
        # change
        old_val = getattr(old_bug, field_name)
        new_val = getattr(new_bug, field_name)
        if old_val != new_val:
            changes[field_name] = new_val

    for field_name in ("name", "private"):
        # fields for which we show old => new when their values change
        old_val = getattr(old_bug, field_name)
        new_val = getattr(new_bug, field_name)
        if old_val != new_val:
            changes[field_name] = {}
            changes[field_name]["old"] = old_val
            changes[field_name]["new"] = new_val

    if changes:
        changes["bug"] = new_bug
        changes["bugurl"] = zapi.absoluteURL(new_bug, request)
        changes["user"] = user

        return BugDelta(**changes)
    else:
        return None


def get_task_delta(old_task, new_task):
    """Compute the delta from old_task to new_task.

    old_task and new_task are either both IDistroBugTask's or both
    IUpstreamBugTask's, otherwise a TypeError is raised.

    Returns an IBugTaskDelta or None if there were no changes between
    old_task and new_task.
    """
    changes = {}
    if (IUpstreamBugTask.providedBy(old_task) and
        IUpstreamBugTask.providedBy(new_task)):
        if old_task.product != new_task.product:
            changes["product"] = {}
            changes["product"]["old"] = old_task.product
            changes["product"]["new"] = new_task.product
        # milestone is only used by upstream (and is a hack that was
        # done for upstream in lieu of a "todo" application that
        # handles this sort of functionality.)
        if old_task.milestone != new_task.milestone:
            changes["milestone"] = {}
            changes["milestone"]["old"] = old_task.milestone
            changes["milestone"]["new"] = new_task.milestone
    elif (IDistroBugTask.providedBy(old_task) and
          IDistroBugTask.providedBy(new_task)):
        if old_task.sourcepackagename != new_task.sourcepackagename:
            changes["sourcepackagename"] = {}
            changes["sourcepackagename"]["old"] = old_task.sourcepackagename
            changes["sourcepackagename"]["new"] = new_task.sourcepackagename
        if old_task.binarypackagename != new_task.binarypackagename:
            changes["binarypackagename"] = {}
            changes["binarypackagename"]["old"] = old_task.binarypackagename
            changes["binarypackagename"]["new"] = new_task.binarypackagename
    else:
        raise TypeError(
            "Can't calculate delta on bug tasks of incompatible types: "
            "[%s, %s]" % (repr(old_task), repr(new_task)))

    # calculate the differences in the fields that both types of tasks
    # have in common
    for field_name in ("status", "severity", "priority"):
        old_val = getattr(old_task, field_name)
        new_val = getattr(new_task, field_name)
        if old_val != new_val:
            changes[field_name] = {}
            changes[field_name]["old"] = old_val
            changes[field_name]["new"] = new_val

    old_assignee = getattr(old_task, "assignee")
    new_assignee = getattr(new_task, "assignee")
    if old_assignee != new_assignee:
        changes["assignee"] = {}
        changes["assignee"]["old"] = old_assignee
        changes["assignee"]["new"] = new_assignee

    if changes:
        changes["bugtask"] = old_task
        return BugTaskDelta(**changes)
    else:
        return None


def notify_bug_added(bug_add_form, event):
    """Send an email notification that a bug was added.

    bug_add_form must be an IBugAddForm. event must be an
    ISQLObjectCreatedEvent.
    """

    # get the real bug first, to ensure that things like view lookups
    # (e.g. for the absolute URL) and attribute access in the code
    # below Just Work.
    bug = getUtility(IBugSet).get(bug_add_form.id)
    notification_recipient_emails = get_cc_list(bug)

    if notification_recipient_emails:
        owner = "(no owner)"
        spname = "(none)"
        pname = "(none)"
        if bug.owner:
            owner = bug.owner.displayname
        if bug.bugtasks[0].sourcepackagename:
            spname = bug.bugtasks[0].sourcepackagename.name
        if bug.bugtasks[0].product:
            pname = bug.bugtasks[0].product.displayname

        msg = """\
Comments and other information can be added to this bug at
%(url)s

Title: %(title)s
Comment: %(comment)s
Source Package: %(source_package)s
Product: %(product)s
Submitted By: %(owner)s
""" % {'url': zapi.absoluteURL(bug, event.request),
       'title' : bug.title,
       'comment' : bug.description,
       'source_package' : spname,
       'product' : pname,
       'owner' : owner}

        simple_sendmail(
            FROM_ADDR, notification_recipient_emails,
            "[Bug %d] %s" % (bug.id, bug.title), msg)

def notify_bug_modified(modified_bug, event):
    """Notify the Cc'd list that this bug has been modified.

    modified_bug bug must be an IBug. event must be an
    ISQLObjectModifiedEvent.
    """
    notification_recipient_emails = get_cc_list(modified_bug)

    if notification_recipient_emails:
        bug_delta = get_bug_delta(
            old_bug = event.object_before_modification,
            new_bug = event.object,
            user = IPerson(event.principal),
            request = event.request)
        send_bug_edit_notification(
            from_addr = FROM_ADDR,
            to_addrs = notification_recipient_emails,
            bug_delta = bug_delta)

def notify_bugtask_added(bugtask, event):
    """Notify CC'd list that this bug has been marked as needing fixing
    somewhere else.

    bugtask must be in IBugTask. event must be an
    ISQLObjectModifiedEvent.
    """
    bugtask = event.object
    notification_recipient_emails = get_cc_list(bugtask.bug)

    if notification_recipient_emails:
        assignee_name = "(not assigned)"

        msg = (
            "Comments and other information can be added to this bug at\n" +
            zapi.absoluteURL(bugtask.bug, event.request) + "\n\n")

        if bugtask.product:
            msg += "Upstream: %s" % bugtask.product.displayname
        elif bugtask.distribution:
            msg += "Distribution: %s" % bugtask.distribution.displayname
        elif bugtask.distrorelease:
            msg += "Distribution Release: %s (%s)" % (
                bugtask.distrorelease.distribution.displayname,
                bugtask.distrorelease.displayname)
        else:
            raise TypeError("Unrecognized BugTask type")

        simple_sendmail(
            FROM_ADDR, notification_recipient_emails,
            "[Bug %d] %s" % (bugtask.bug.id, bugtask.bug.title), msg)

def notify_bugtask_edited(modified_bugtask, event):
    """Notify CC'd subscribers of this bug that something has changed
    on this task.

    modified_bugtask must be an IBugTask. event must be an
    ISQLObjectModifiedEvent.
    """
    task = event.object
    notification_recipient_emails = get_cc_list(task.bug)

    if notification_recipient_emails:
        bugtask_delta = get_task_delta(
            event.object_before_modification, event.object)
        bug_delta = BugDelta(
            bug = event.object.bug,
            bugurl = zapi.absoluteURL(event.object.bug, event.request),
            bugtask_deltas = bugtask_delta,
            user = IPerson(event.principal))
        send_bug_edit_notification(
            from_addr = FROM_ADDR, to_addrs = notification_recipient_emails,
            bug_delta = bug_delta)

def notify_bug_product_infestation_added(product_infestation, event):
    """Notify CC'd list that this bug has infested a product release.

    product_infestation must be an IBugProductInfestation. event must
    be an ISQLObjectCreatedEvent.
    """
    notification_recipient_emails = get_cc_list(product_infestation.bug)

    if notification_recipient_emails:
        msg = """\
Product: %(product)s
Infestation: %(infestation)s
""" % {'product' :
             product_infestation.productrelease.product.name + " " +
             product_infestation.productrelease.version,
           'infestation' : product_infestation.infestationstatus.title}

        simple_sendmail(
            FROM_ADDR, notification_recipient_emails,
            "[Bug %d] %s" % (
                product_infestation.bug.id,
                product_infestation.bug.title),
            msg)

def notify_bug_product_infestation_modified(modified_product_infestation, event):
    """Notify CC'd list that this product infestation has been edited.

    modified_product_infestation must be an IBugProductInfestation. event must
    be an ISQLObjectModifiedEvent.
    """
    notification_recipient_emails = get_cc_list(modified_product_infestation.bug)

    if notification_recipient_emails:
        changes = get_changes(
            before = event.object_before_modification,
            after = event.object,
            fields = (
                ("productrelease", lambda v: "%s %s" % (
                    v.product.name, v.version)),
                ("infestationstatus", lambda v: v.title)))

        send_bug_edit_notification(
            bug = modified_product_infestation.bug,
            from_addr = FROM_ADDR,
            to_addrs = notification_recipient_emails,
            subject = "[Bug %d] %s" % (
                 modified_product_infestation.bug.id,
                 modified_product_infestation.bug.title),
            edit_header_line = (
                "Edited infested product: %s" %
                event.object_before_modification.productrelease.product.displayname + " " +
                event.object_before_modification.productrelease.version),
            changes = changes, user = event.principal)

def notify_bug_package_infestation_added(package_infestation, event):
    """Notify CC'd list that this bug has infested a source package
    release.


    package_infestation must be an IBugPackageInfestation. event must
    be an ISQLObjectCreatedEvent.
    """
    notification_recipient_emails = get_cc_list(package_infestation.bug)

    if notification_recipient_emails:
        msg = """\
Source Package: %(package)s
Infestation: %(infestation)s
""" % {'package' :
           package_infestation.sourcepackagerelease.name + " " +
           package_infestation.sourcepackagerelease.version,
       'infestation' : package_infestation.infestationstatus.title}

        simple_sendmail(
            FROM_ADDR, notification_recipient_emails,
            "[Bug %d] %s" % (
                package_infestation.bug.id,
                package_infestation.bug.title),
            msg)

def notify_bug_package_infestation_modified(modified_package_infestation, event):
    """Notify CC'd list that this package infestation has been
    modified.

    modified_package_infestation must be an IBugPackageInfestation. event
    must be an ISQLObjectModifiedEvent.
    """
    notification_recipient_emails = get_cc_list(modified_package_infestation.bug)

    if notification_recipient_emails:
        changes = get_changes(
            before = event.object_before_modification,
            after = event.object,
            fields = (
                ("sourcepackagerelease", lambda v: "%s %s" % (
                    v.sourcepackagename.name, v.version)),
                ("infestationstatus", lambda v: v.title)))

        send_bug_edit_notification(
            bug = modified_package_infestation.bug, from_addr = FROM_ADDR,
            to_addrs = notification_recipient_emails,
            subject = "[Bug %d] %s" % (
                modified_package_infestation.bug.id,
                modified_package_infestation.bug.title),
            edit_header_line = (
                "Edited infested package: %s" %
                event.object_before_modification.sourcepackagerelease.sourcepackagename.name + " " +
                event.object_before_modification.sourcepackagerelease.version),
            changes = changes, user = event.principal)

def notify_bug_comment_added(bugmessage, event):
    """Notify CC'd list that a message was added to this bug.

    bugmessage must be an IBugMessage. event must be an
    ISQLObjectCreatedEvent.
    """
    notification_recipient_emails = get_cc_list(bugmessage.bug)

    if notification_recipient_emails:
        msg = """\
Comments and other information can be added to this bug at
%(url)s

%(submitter)s said:

%(subject)s

%(contents)s""" % {
            'url' : zapi.absoluteURL(bugmessage.bug, event.request),
            'submitter' :bugmessage.message.owner.displayname,
            'subject' : bugmessage.message.title,
            'contents' : bugmessage.message.contents}

        simple_sendmail(
            FROM_ADDR, notification_recipient_emails,
            "[Bug %d] %s" % (
                bugmessage.bug.id, bugmessage.bug.title),
            msg)

def notify_bug_external_ref_added(ext_ref, event):
    """Notify CC'd list that a new web link has been added for this
    bug.

    ext_ref must be an IBugExternalRef. event must be an
    ISQLObjectCreatedEvent.
    """
    notification_recipient_emails = get_cc_list(ext_ref.bug)

    if notification_recipient_emails:
        bug_delta = BugDelta(
            bug = ext_ref.bug,
            bugurl = zapi.absoluteURL(ext_ref.bug, event.request),
            user = IPerson(event.request.principal),
            external_reference = {'new' : ext_ref})

        send_bug_edit_notification(
            FROM_ADDR, notification_recipient_emails, bug_delta)

def notify_bug_external_ref_edited(edited_ext_ref, event):
    """Notify CC'd list that a web link has been edited.

    edited_ext_ref must be an IBugExternalRef. event must be an
    ISQLObjectModifiedEvent.
    """
    notification_recipient_emails = get_cc_list(edited_ext_ref.bug)

    if notification_recipient_emails:
        old = event.object_before_modification
        new = event.object
        if ((old.url != new.url) or (old.title != new.title)):
            # A change was made that's worth sending an edit
            # notification about.
            bug_delta = BugDelta(
                bug = new.bug,
                bugurl = zapi.absoluteURL(new.bug, event.request),
                user = IPerson(event.request.principal),
                external_reference = {'old' : old, 'new' : new})

            send_bug_edit_notification(
                FROM_ADDR, notification_recipient_emails, bug_delta)

def notify_bug_watch_added(watch, event):
    """Notify CC'd list that a new watch has been added for this bug.

    watch must be an IBugWatch. event must be an
    ISQLObjectCreatedEvent.
    """
    notification_recipient_emails = get_cc_list(watch.bug)

    if notification_recipient_emails:
        bug_delta = BugDelta(
            bug = watch.bug,
            bugurl = zapi.absoluteURL(watch.bug, event.request),
            user = IPerson(event.request.principal),
            bugwatch = {'new' : watch})

        send_bug_edit_notification(
            FROM_ADDR, notification_recipient_emails, bug_delta)

def notify_bug_watch_modified(modified_bug_watch, event):
    """Notify CC'd bug subscribers that a bug watch was edited.

    modified_bug_watch must be an IBugWatch. event must be an
    ISQLObjectModifiedEvent.
    """
    notification_recipient_emails = get_cc_list(modified_bug_watch.bug)

    if notification_recipient_emails:
        old = event.object_before_modification
        new = event.object
        if ((old.bugtracker != new.bugtracker) or
            (old.remotebug != new.remotebug)):
            # there is a difference worth notifying about here
            # so let's keep going
            bug_delta = BugDelta(
                bug = new.bug,
                bugurl = zapi.absoluteURL(new.bug, event.request),
                user = IPerson(event.request.principal),
                bugwatch = {'old' : old, 'new' : new})
            send_bug_edit_notification(
                from_addr = FROM_ADDR,
                to_addrs = notification_recipient_emails,
                bug_delta = bug_delta)

def notify_bug_cveref_added(cveref, event):
    """Notify CC'd list that a new cveref has been added to this bug.

    cveref must be an ICVERef. event must be an
    ISQLObjectCreatedEvent.
    """
    notification_recipient_emails = get_cc_list(cveref.bug)

    if notification_recipient_emails:
        bug_delta = BugDelta(
            bug = cveref.bug,
            bugurl = zapi.absoluteURL(cveref.bug, event.request),
            user = IPerson(event.request.principal),
            cveref = {'new': cveref})

        send_bug_edit_notification(
            FROM_ADDR, notification_recipient_emails, bug_delta)

def notify_bug_cveref_edited(edited_cveref, event):
    """Notify CC'd list that a cveref has been edited.

    edited_cveref must be an ICVERef. event must be an
    ISQLObjectModifiedEvent.
    """
    notification_recipient_emails = get_cc_list(edited_cveref.bug)

    if notification_recipient_emails:
        old = event.object_before_modification
        new = event.object
        if ((old.cveref != new.cveref) or (old.title != new.title)):
            # There's a change worth notifying about, so let's go
            # ahead and send a notification email.
            bug_delta = BugDelta(
                bug = new.bug,
                bugurl = zapi.absoluteURL(new.bug, event.request),
                user = IPerson(event.request.principal),
                cveref = {'old' : old, 'new': new})

            send_bug_edit_notification(
                FROM_ADDR, notification_recipient_emails, bug_delta)

def notify_join_request(event):
    """Notify team administrators that a new membership is pending approval."""
    # XXX: salgado, 2005-05-06: I have an implementation of __contains__ for 
    # SelectResults, and as soon as it's merged we'll be able to replace this
    # uggly for/else block by an 
    # "if not event.user in event.team.proposedmembers: return".
    for member in event.team.proposedmembers:
        if member == event.user:
            break
    else:
        return

    user = event.user
    team = event.team
    to_addrs = []
    for person in itertools.chain(team.administrators, [team.teamowner]):
        for member in person.allmembers:
            if ITeam.providedBy(member):
                # Don't worry, this is a team and person.allmembers already
                # gave us all members of this team too.
                pass
            elif (member.preferredemail is not None and
                  member.preferredemail.email not in to_addrs):
                to_addrs.append(member.preferredemail.email)

    if to_addrs:
        url = "%s/people/%s/+members/%s" % (event.appurl, team.name, user.name)
        replacements = {'browsername': user.browsername,
                        'name': user.name,
                        'teamname': team.browsername,
                        'url': url}
        file = 'lib/canonical/launchpad/templates/pending-membership-approval.txt'
        msg = open(file).read() % replacements
        fromaddress = "Launchpad <launchpad@ubuntu.com>"
        subject = "Launchpad: New member awaiting approval."
        simple_sendmail(fromaddress, to_addrs, subject, msg)
