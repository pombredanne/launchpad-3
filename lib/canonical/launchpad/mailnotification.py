"""mailer.py -- Handle all mail notification done in the Launchpad
application."""

from zope.app import zapi
from zope.app.mail.interfaces import IMailDelivery
from zope.component import getUtility

from canonical.launchpad.interfaces import IBug, IBugSet, ITeam
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
                changed_field, changes[changed_field]["old"],
                changes[changed_field]["new"])

        send_edit_notification_simple(bug, from_addr, to_addrs, subject, msg)

def get_cc_list(bug):
    """Return the list of people that are CC'd on this bug."""
    subscriptions = []
    if not bug.private:
        subscriptions = list(GLOBAL_NOTIFICATION_EMAIL_ADDRS)

    subscriptions += bug.notificationRecipientAddresses()

    return subscriptions

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
    """Send an email notification that a bug was added."""

    # get the real bug first, to ensure that things like view lookups
    # (e.g. for the absolute URL) and attribute access in the code
    # below Just Work.
    bug = getUtility(IBugSet).get(bug_add_form.id)

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
Bug URL: %(url)s

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

    edit_header_line = """\
Edited bug: %(title)s

Bug URL: %(url)s""" % {
        'title' : event.object_before_modification.title,
        'url' : zapi.absoluteURL(event.object, event.request)}

    send_edit_notification(
        bug = modified_bug,
        from_addr = FROM_ADDR,
        to_addrs = get_cc_list(modified_bug),
        subject = '"%s" edited' % event.object_before_modification.title,
        edit_header_line = edit_header_line,
        changes = changes)

def notify_bugtask_added(bugtask, event):
    """Notify CC'd list that this bug has been marked as needing fixing
    somewhere else."""
    bugtask = event.object
    assignee_name = "(not assigned)"

    msg = "Bug URL: %s\n\n" % zapi.absoluteURL(bugtask.bug, event.request)

    if bugtask.product:
        msg += "Upstream: %s" % bugtask.product.displayname
    elif bugtask.distribution:
        msg += "Distribution: %s" % bugtask.distribution.displayname
    elif bugtask.distrorelease:
        msg += "Distribution Release: %s (%s)" % (
            bugtask.distrorelease.distribution.displayname,
            bugtask.distrorelease.displayname)
    else:
        raise ValueError("Unrecognized BugTask type")

    send_edit_notification_simple(
        bugtask.bug, FROM_ADDR, get_cc_list(bugtask.bug),
        '"%s" task added' % bugtask.bug.title, msg)

def notify_bugtask_edited(modified_bugtask, event):
    """Notify CC'd subscribers of this bug that something has changed on this
    task."""
    task = event.object
    changes = get_changes(
        before = event.object_before_modification,
        after = task,
        fields = (
            ("status", lambda v: v.title),
            ("priority", lambda v: v.title),
            ("severity", lambda v: v.title),
            ("binarypackagename", lambda v: (v and v.name) or "(none)"),
            ("assignee", lambda v: (v and v.displayname) or "(not assigned)")))

    where = None
    if task.product:
        where = "upstream " + task.product.name
    elif task.distribution:
        where = task.distribution.name
    elif task.distrorelease:
        where = "%s %s" % (
            task.distrorelease.distribution.name, task.distrorelease.name)

    edit_header_line = """\
Edited task on %(where)s

Bug URL: %(url)s""" % {
        'where' : where, 'url' : zapi.absoluteURL(task.bug, event.request)}

    send_edit_notification(
        bug = task.bug, from_addr = FROM_ADDR,
        to_addrs = get_cc_list(task.bug),
        subject = '"%s" task edited' % task.bug.title,
        edit_header_line = edit_header_line,
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
       'infestation' : product_infestation.infestationstatus.title}

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
            ("infestationstatus", lambda v: v.title)))

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
         package_infestation.sourcepackagerelease.name + " " +
         package_infestation.sourcepackagerelease.version,
       'infestation' : package_infestation.infestationstatus.title}

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
                v.sourcepackagename.name, v.version)),
            ("infestationstatus", lambda v: v.title)))

    send_edit_notification(
        bug = modified_package_infestation.bug,
        from_addr = FROM_ADDR,
        to_addrs = get_cc_list(modified_package_infestation.bug),
        subject = '"%s" package infestation edited' % modified_package_infestation.bug.title,
        edit_header_line = (
            "Edited infested package: %s" %
            event.object_before_modification.sourcepackagerelease.sourcepackagename.name + " " +
            event.object_before_modification.sourcepackagerelease.version),
        changes = changes)

def notify_bug_comment_added(bugmessage, event):
    """Notify CC'd list that a message was added to this bug."""
    msg = """\
Bug URL: %(url)s

%(submitter)s said:

%(subject)s

%(contents)s""" % {
        'url' : zapi.absoluteURL(bugmessage.bug, event.request),
        'submitter' :bugmessage.message.owner.displayname,
        'subject' : bugmessage.message.title,
        'contents' : bugmessage.message.contents}

    send_edit_notification_simple(
        bugmessage.bug,
        FROM_ADDR, get_cc_list(bugmessage.bug),
        '"%s" comment added' % bugmessage.bug.title, msg)

def notify_bug_external_ref_added(ext_ref, event):
    """Notify CC'd list that a new web link has
    been added for this bug."""
    msg = """\
Bug URL: %(bugurl)s

URL: %(url)s
Title: %(title)s
""" % {'bugurl' : zapi.absoluteURL(ext_ref.bug, event.request),
       'url' : ext_ref.url, 'title' : ext_ref.title}

    send_edit_notification_simple(
        ext_ref.bug,
        FROM_ADDR, get_cc_list(ext_ref.bug),
        '"%s" web link added' % ext_ref.bug.title, msg)

def notify_bug_watch_added(watch, event):
    """Notify CC'd list that a new watch has been added for this
    bug."""
    msg = """\
Bug URL: %(bugurl)s

Bug Tracker: %(bug_tracker)s
Remote Bug: %(remote_bug)s
""" % {'bugurl' : zapi.absoluteURL(watch.bug, event.request),
       'bug_tracker' : watch.bugtracker.title, 'remote_bug' : watch.remotebug}

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

    edit_header_line = """\
Edited watch on bugtracker: %(bugtracker)s

Bug URL: %(url)s""" % {
        'bugtracker' : event.object_before_modification.bugtracker.title,
        'url' : zapi.absoluteURL(modified_bug_watch.bug, event.request)}

    send_edit_notification(
        bug = event.object_before_modification.bug,
        from_addr = FROM_ADDR,
        to_addrs = get_cc_list(modified_bug_watch.bug),
        subject = '"%s" watch edited' % event.object_before_modification.bug.title,
        edit_header_line = edit_header_line,
        changes = changes)


def notify_join_request(event):
    """Notify team administrators that a new membership is pending approval."""
    if not event.user in event.team.proposedmembers:
        return

    user = event.user
    team = event.team
    to_addrs = []
    for person in team.administrators + [team.teamowner]:
        for member in person.allmembers:
            if ITeam.providedBy(member):
                # Don't worry, this is a team and person.allmembers already
                # gave us all members of this team too.
                pass
            elif (member.preferredemail is not None and
                  member.preferredemail.email not in to_addrs):
                to_addrs.append(member.preferredemail.email)

    url = "%s/people/%s/+members/%s" % (event.appurl, team.name, user.name)
    replacements = {'browsername': user.browsername(),
                    'name': user.name,
                    'teamname': team.browsername(),
                    'url': url}
    file = 'lib/canonical/launchpad/templates/pending-membership-approval.txt'
    msg = open(file).read() % replacements
    fromaddress = "Launchpad <launchpad@ubuntu.com>"
    subject = "Launchpad: New member awayting approval."
    simple_sendmail(fromaddress, to_addrs, subject, msg)

