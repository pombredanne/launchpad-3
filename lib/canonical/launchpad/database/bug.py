# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""Launchpad bug-related database table classes."""

__metaclass__ = type

__all__ = [
    'Bug', 'BugBecameQuestionEvent', 'BugSet', 'get_bug_tags',
    'get_bug_tags_open_count']


import operator
import re
from cStringIO import StringIO
from email.Utils import make_msgid

from zope.app.content_types import guess_content_type
from zope.component import getUtility
from zope.event import notify
from zope.interface import implements, providedBy

from sqlobject import BoolCol, IntCol, ForeignKey, StringCol
from sqlobject import SQLMultipleJoin, SQLRelatedJoin
from sqlobject import SQLObjectNotFound

from canonical.launchpad.interfaces import (
    BugAttachmentType, BugTaskStatus, BugTrackerType, DistroSeriesStatus,
    IBug, IBugAttachmentSet, IBugBecameQuestionEvent, IBugBranch,
    IBugNotificationSet, IBugSet, IBugTaskSet, IBugWatchSet, ICveSet,
    IDistribution, IDistroSeries, ILaunchpadCelebrities, ILibraryFileAliasSet,
    IMessage, IPersonSet, IProduct, IProductSeries, IQuestionTarget,
    ISourcePackage, IStructuralSubscriptionTarget, NominationError,
    NominationSeriesObsoleteError, NotFoundError, UNRESOLVED_BUGTASK_STATUSES)
from canonical.launchpad.helpers import shortlist
from canonical.database.sqlbase import cursor, SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.database.bugbranch import BugBranch
from canonical.launchpad.database.bugcve import BugCve
from canonical.launchpad.database.bugnomination import BugNomination
from canonical.launchpad.database.bugnotification import BugNotification
from canonical.launchpad.database.message import (
    MessageSet, Message, MessageChunk)
from canonical.launchpad.database.bugmessage import BugMessage
from canonical.launchpad.database.bugtask import (
    BugTask,
    BugTaskSet,
    bugtask_sort_key,
    get_bug_privacy_filter,
    NullBugTask,
    )
from canonical.launchpad.database.bugwatch import BugWatch
from canonical.launchpad.database.bugsubscription import BugSubscription
from canonical.launchpad.database.mentoringoffer import MentoringOffer
from canonical.launchpad.database.person import Person
from canonical.launchpad.database.pillar import pillar_sort_key
from canonical.launchpad.validators.person import public_person_validator
from canonical.launchpad.event.sqlobjectevent import (
    SQLObjectCreatedEvent, SQLObjectDeletedEvent, SQLObjectModifiedEvent)
from canonical.launchpad.mailnotification import BugNotificationRecipients
from canonical.launchpad.webapp.snapshot import Snapshot


_bug_tag_query_template = """
        SELECT %(columns)s FROM %(tables)s WHERE
            %(condition)s GROUP BY BugTag.tag ORDER BY BugTag.tag"""


def get_bug_tags(context_clause):
    """Return all the bug tags as a list of strings.

    context_clause is a SQL condition clause, limiting the tags to a
    specific context. The SQL clause can only use the BugTask table to
    choose the context.
    """
    from_tables = ['BugTag', 'BugTask']
    select_columns = ['BugTag.tag']
    conditions = ['BugTag.bug = BugTask.bug', '(%s)' % context_clause]

    cur = cursor()
    cur.execute(_bug_tag_query_template % dict(
            columns=', '.join(select_columns),
            tables=', '.join(from_tables),
            condition=' AND '.join(conditions)))
    return shortlist([row[0] for row in cur.fetchall()])


def get_bug_tags_open_count(maincontext_clause, user,
                            count_subcontext_clause=None):
    """Return all the used bug tags with their open bug count.

    maincontext_clause is a SQL condition clause, limiting the used tags
    to a specific context.
    count_subcontext_clause is a SQL condition clause, limiting the open bug
    count to a more limited context, for example a source package.

    Both SQL clauses may only use the BugTask table to choose the context.
    """
    from_tables = ['BugTag', 'BugTask', 'Bug']
    count_conditions = ['BugTask.status IN (%s)' % ','.join(
        sqlvalues(*UNRESOLVED_BUGTASK_STATUSES))]
    if count_subcontext_clause:
        count_conditions.append(count_subcontext_clause)
    select_columns = [
        'BugTag.tag',
        'COUNT (CASE WHEN %s THEN Bug.id ELSE NULL END)' %
            ' AND '.join(count_conditions),
        ]
    conditions = [
        'BugTag.bug = BugTask.bug',
        'Bug.id = BugTag.bug',
        '(%s)' % maincontext_clause]
    privacy_filter = get_bug_privacy_filter(user)
    if privacy_filter:
        conditions.append(privacy_filter)

    cur = cursor()
    cur.execute(_bug_tag_query_template % dict(
            columns=', '.join(select_columns),
            tables=', '.join(from_tables),
            condition=' AND '.join(conditions)))
    return shortlist([(row[0], row[1]) for row in cur.fetchall()])


class BugTag(SQLBase):
    """A tag belonging to a bug."""

    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    tag = StringCol(notNull=True)


class BugBecameQuestionEvent:
    """See `IBugBecameQuestionEvent`."""
    implements(IBugBecameQuestionEvent)

    def __init__(self, bug, question, user):
        self.bug = bug
        self.question = question
        self.user = user


class Bug(SQLBase):
    """A bug."""

    implements(IBug)

    _defaultOrder = '-id'

    # db field names
    name = StringCol(unique=True, default=None)
    title = StringCol(notNull=True)
    description = StringCol(notNull=False,
                            default=None)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person',
        validator=public_person_validator, notNull=True)
    duplicateof = ForeignKey(
        dbName='duplicateof', foreignKey='Bug', default=None)
    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    date_last_updated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    private = BoolCol(notNull=True, default=False)
    date_made_private = UtcDateTimeCol(notNull=False, default=None)
    who_made_private = ForeignKey(
        dbName='who_made_private', foreignKey='Person',
        validator=public_person_validator, default=None)
    security_related = BoolCol(notNull=True, default=False)

    # useful Joins
    activity = SQLMultipleJoin('BugActivity', joinColumn='bug', orderBy='id')
    messages = SQLRelatedJoin('Message', joinColumn='bug',
                           otherColumn='message',
                           intermediateTable='BugMessage',
                           prejoins=['owner'],
                           orderBy=['datecreated', 'id'])
    productinfestations = SQLMultipleJoin(
            'BugProductInfestation', joinColumn='bug', orderBy='id')
    packageinfestations = SQLMultipleJoin(
            'BugPackageInfestation', joinColumn='bug', orderBy='id')
    watches = SQLMultipleJoin(
        'BugWatch', joinColumn='bug', orderBy=['bugtracker', 'remotebug'])
    cves = SQLRelatedJoin('Cve', intermediateTable='BugCve',
        orderBy='sequence', joinColumn='bug', otherColumn='cve')
    cve_links = SQLMultipleJoin('BugCve', joinColumn='bug', orderBy='id')
    mentoring_offers = SQLMultipleJoin(
            'MentoringOffer', joinColumn='bug', orderBy='id')
    # XXX: kiko 2006-09-23: Why is subscriptions ordered by ID?
    subscriptions = SQLMultipleJoin(
            'BugSubscription', joinColumn='bug', orderBy='id',
            prejoins=["person"])
    duplicates = SQLMultipleJoin(
        'Bug', joinColumn='duplicateof', orderBy='id')
    attachments = SQLMultipleJoin('BugAttachment', joinColumn='bug',
        orderBy='id', prejoins=['libraryfile'])
    specifications = SQLRelatedJoin('Specification', joinColumn='bug',
        otherColumn='specification', intermediateTable='SpecificationBug',
        orderBy='-datecreated')
    questions = SQLRelatedJoin('Question', joinColumn='bug',
        otherColumn='question', intermediateTable='QuestionBug',
        orderBy='-datecreated')
    bug_branches = SQLMultipleJoin(
        'BugBranch', joinColumn='bug', orderBy='id')
    date_last_message = UtcDateTimeCol(default=None)
    number_of_duplicates = IntCol(notNull=True, default=0)
    message_count = IntCol(notNull=True, default=0)

    @property
    def displayname(self):
        """See `IBug`."""
        dn = 'Bug #%d' % self.id
        if self.name:
            dn += ' ('+self.name+')'
        return dn

    @property
    def bugtasks(self):
        """See `IBug`."""
        result = BugTask.select('BugTask.bug = %s' % sqlvalues(self.id))
        result = result.prejoin(
            ["assignee", "product", "sourcepackagename",
             "owner", "bugwatch"])
        # Do not use the defaul orderBy as the prejoins cause ambiguities
        # across the tables.
        result = result.orderBy("id")
        return sorted(result, key=bugtask_sort_key)

    @property
    def is_complete(self):
        """See `IBug`."""
        for task in self.bugtasks:
            if not task.is_complete:
                return False
        return True

    @property
    def affected_pillars(self):
        """See `IBug`."""
        result = set()
        for task in self.bugtasks:
            result.add(task.pillar)
        return sorted(result, key=pillar_sort_key)

    @property
    def permits_expiration(self):
        """See `IBug`.

        This property checks the general state of the bug to determine if
        expiration is permitted *if* a bugtask were to qualify for expiration.
        This property does not check the bugtask preconditions to identify
        a specific bugtask that can expire.

        :See: `IBug.can_expire` or `BugTaskSet.findExpirableBugTasks` to
            check or get a list of bugs that can expire.
        """
        # Bugs cannot be expired if any bugtask is valid.
        expirable_status_list = [
            BugTaskStatus.INCOMPLETE, BugTaskStatus.INVALID,
            BugTaskStatus.WONTFIX]
        has_an_expirable_bugtask = False
        for bugtask in self.bugtasks:
            if bugtask.status not in expirable_status_list:
                # We found an unexpirable bugtask; the bug cannot expire.
                return False
            if (bugtask.status == BugTaskStatus.INCOMPLETE
                and bugtask.pillar.enable_bug_expiration):
                # This bugtasks meets the basic conditions to expire.
                has_an_expirable_bugtask = True

        return has_an_expirable_bugtask

    @property
    def can_expire(self):
        """See `IBug`.

        Only Incomplete bug reports that affect a single pillar with
        enabled_bug_expiration set to True can be expired. To qualify for
        expiration, the bug and its bugtasks meet the follow conditions:

        1. The bug is inactive; the last update of the is older than
            Launchpad expiration age.
        2. The bug is not a duplicate.
        3. The bug has at least one message (a request for more information).
        4. The bug does not have any other valid bugtasks.
        5. The bugtask belongs to a project with enable_bug_expiration set
           to True.
        6. The bugtask has the status Incomplete.
        7. The bugtask is not assigned to anyone.
        8. The bugtask does not have a milestone.
        """
        # IBugTaskSet.findExpirableBugTasks() is the authoritative determiner
        # if a bug can expire, but it is expensive. We do a general check
        # to verify the bug permits expiration before using IBugTaskSet to
        # determine if a bugtask can cause expiration.
        if not self.permits_expiration:
            return False

        # Do the search as the Janitor, to ensure that this bug can be
        # found, even if it's private. We don't have access to the user
        # calling this property. If the user has access to view this
        # property, he has permission to see the bug, so we're not
        # exposing something we shouldn't. The Janitor has access to
        # view all bugs.
        bugtasks = getUtility(IBugTaskSet).findExpirableBugTasks(
            0, getUtility(ILaunchpadCelebrities).janitor, bug=self)
        return bugtasks.count() > 0

    @property
    def initial_message(self):
        """See `IBug`."""
        messages = sorted(self.messages, key=lambda ob: ob.id)
        return messages[0]

    def followup_subject(self):
        """See `IBug`."""
        return 'Re: '+ self.title

    def subscribe(self, person, subscribed_by):
        """See `IBug`."""
        # first look for an existing subscription
        for sub in self.subscriptions:
            if sub.person.id == person.id:
                return sub

        sub = BugSubscription(
            bug=self, person=person, subscribed_by=subscribed_by)
        notify(SQLObjectCreatedEvent(sub))
        return sub

    def unsubscribe(self, person):
        """See `IBug`."""
        for sub in self.subscriptions:
            if sub.person.id == person.id:
                BugSubscription.delete(sub.id)
                return

    def unsubscribeFromDupes(self, person):
        """See `IBug`."""
        bugs_unsubscribed = []
        for dupe in self.duplicates:
            if dupe.isSubscribed(person):
                dupe.unsubscribe(person)
                bugs_unsubscribed.append(dupe)

        return bugs_unsubscribed

    def isSubscribed(self, person):
        """See `IBug`."""
        if person is None:
            return False

        bs = BugSubscription.selectBy(bug=self, person=person)
        return bool(bs)

    def isSubscribedToDupes(self, person):
        """See `IBug`."""
        return bool(
            BugSubscription.select("""
                bug IN (SELECT id FROM Bug WHERE duplicateof = %d) AND
                person = %d""" % (self.id, person.id)))

    def getDirectSubscriptions(self):
        """See `IBug`."""
        return BugSubscription.select("""
            Person.id = BugSubscription.person AND
            BugSubscription.bug = %d""" % self.id,
            orderBy="displayname", clauseTables=["Person"])

    def getDirectSubscribers(self, recipients=None):
        """See `IBug`.

        The recipients argument is private and not exposed in the
        inerface. If a BugNotificationRecipients instance is supplied,
        the relevant subscribers and rationales will be registered on
        it.
        """
        subscribers = list(
            Person.select("""
                Person.id = BugSubscription.person AND
                BugSubscription.bug = %d""" % self.id,
                orderBy="displayname", clauseTables=["BugSubscription"]))
        if recipients is not None:
            for subscriber in subscribers:
                recipients.addDirectSubscriber(subscriber)
        return subscribers

    def getIndirectSubscribers(self, recipients=None):
        """See `IBug`.

        See the comment in getDirectSubscribers for a description of the
        recipients argument.
        """
        # "Also notified" and duplicate subscribers are mutually
        # exclusive, so return both lists.
        indirect_subscribers = (
            self.getAlsoNotifiedSubscribers(recipients) +
            self.getSubscribersFromDuplicates(recipients))

        return sorted(
            indirect_subscribers, key=operator.attrgetter("displayname"))

    def getSubscriptionsFromDuplicates(self, recipients=None):
        """See `IBug`."""
        if self.private:
            return []

        duplicate_subscriptions = set(
            BugSubscription.select("""
                BugSubscription.bug = Bug.id AND
                Bug.duplicateof = %d""" % self.id,
                clauseTables=["Bug"]))

        # Direct and "also notified" subscribers take precedence
        # over subscribers from duplicates.
        duplicate_subscriptions -= set(self.getDirectSubscriptions())
        also_notified_subscriptions = set()
        for also_notified_subscriber in self.getAlsoNotifiedSubscribers():
            for duplicate_subscription in duplicate_subscriptions:
                if also_notified_subscriber == duplicate_subscription.person:
                    also_notified_subscriptions.add(duplicate_subscription)
                    break
        duplicate_subscriptions -= also_notified_subscriptions

        # Only add a subscriber once to the list.
        duplicate_subscribers = set(
            sub.person for sub in duplicate_subscriptions)
        subscriptions = []
        for duplicate_subscriber in duplicate_subscribers:
            for duplicate_subscription in duplicate_subscriptions:
                if duplicate_subscription.person == duplicate_subscriber:
                    subscriptions.append(duplicate_subscription)
                    break

        def get_person_displayname(subscription):
            return subscription.person.displayname

        return sorted(subscriptions, key=get_person_displayname)

    def getSubscribersFromDuplicates(self, recipients=None):
        """See `IBug`.

        See the comment in getDirectSubscribers for a description of the
        recipients argument.
        """
        if self.private:
            return []

        dupe_subscribers = set(
            Person.select("""
                Person.id = BugSubscription.person AND
                BugSubscription.bug = Bug.id AND
                Bug.duplicateof = %d""" % self.id,
                clauseTables=["Bug", "BugSubscription"]))

        # Direct and "also notified" subscribers take precedence over
        # subscribers from dupes. Note that we don't supply recipients
        # here because we are doing this to /remove/ subscribers.
        dupe_subscribers -= set(self.getDirectSubscribers())
        dupe_subscribers -= set(self.getAlsoNotifiedSubscribers())

        if recipients is not None:
            for subscriber in dupe_subscribers:
                recipients.addDupeSubscriber(subscriber)

        return sorted(
            dupe_subscribers, key=operator.attrgetter("displayname"))

    def getAlsoNotifiedSubscribers(self, recipients=None):
        """See `IBug`.

        See the comment in getDirectSubscribers for a description of the
        recipients argument.
        """
        if self.private:
            return []

        also_notified_subscribers = set()

        structural_subscription_targets = set()

        for bugtask in self.bugtasks:
            if bugtask.assignee:
                also_notified_subscribers.add(bugtask.assignee)
                if recipients is not None:
                    recipients.addAssignee(bugtask.assignee)

            if IStructuralSubscriptionTarget.providedBy(bugtask.target):
                structural_subscription_targets.add(bugtask.target)
                if bugtask.target.parent_subscription_target is not None:
                    structural_subscription_targets.add(
                        bugtask.target.parent_subscription_target)

            if ISourcePackage.providedBy(bugtask.target):
                # Distribution series bug tasks with a package have the
                # source package set as their target, so we add the
                # distroseries explicitly to the set of subscription
                # targets.
                structural_subscription_targets.add(
                    bugtask.distroseries)

            if bugtask.milestone is not None:
                structural_subscription_targets.add(bugtask.milestone)

            # If the target's bug supervisor isn't set,
            # we add the owner as a subscriber.
            pillar = bugtask.pillar
            if pillar.bug_supervisor is None:
                also_notified_subscribers.add(pillar.owner)
                if recipients is not None:
                    recipients.addRegistrant(pillar.owner, pillar)

        person_set = getUtility(IPersonSet)
        target_subscribers = person_set.getSubscribersForTargets(
            structural_subscription_targets, recipients=recipients)

        also_notified_subscribers.update(target_subscribers)

        # Direct subscriptions always take precedence over indirect
        # subscriptions.
        direct_subscribers = set(self.getDirectSubscribers())
        return sorted(
            (also_notified_subscribers - direct_subscribers),
            key=operator.attrgetter('displayname'))

    def getBugNotificationRecipients(self, duplicateof=None, old_bug=None):
        """See `IBug`."""
        recipients = BugNotificationRecipients(duplicateof=duplicateof)
        self.getDirectSubscribers(recipients)
        if self.private:
            assert self.getIndirectSubscribers() == [], (
                "Indirect subscribers found on private bug. "
                "A private bug should never have implicit subscribers!")
        else:
            self.getIndirectSubscribers(recipients)
            if self.duplicateof:
                # This bug is a public duplicate of another bug, so include
                # the dupe target's subscribers in the recipient list. Note
                # that we only do this for duplicate bugs that are public;
                # changes in private bugs are not broadcast to their dupe
                # targets.
                dupe_recipients = (
                    self.duplicateof.getBugNotificationRecipients(
                        duplicateof=self.duplicateof))
                recipients.update(dupe_recipients)
        # XXX Tom Berger 2008-03-18:
        # We want to look up the recipients for `old_bug` too,
        # but for this to work, this code has to move out of the
        # class and into a free function, since `old_bug` is a
        # `Snapshot`, and doesn't have any of the methods of the
        # original `Bug`.
        return recipients

    def addChangeNotification(self, text, person, recipients=None, when=None):
        """See `IBug`."""
        if recipients is None:
            recipients = self.getBugNotificationRecipients()
        if when is None:
            when = UTC_NOW
        message = MessageSet().fromText(
            self.followup_subject(), text, owner=person, datecreated=when)
        getUtility(IBugNotificationSet).addNotification(
             bug=self, is_comment=False,
             message=message, recipients=recipients)

    def addCommentNotification(self, message, recipients=None):
        """See `IBug`."""
        if recipients is None:
            recipients = self.getBugNotificationRecipients()
        getUtility(IBugNotificationSet).addNotification(
             bug=self, is_comment=True,
             message=message, recipients=recipients)

    def expireNotifications(self):
        """See `IBug`."""
        for notification in BugNotification.selectBy(
                bug=self, date_emailed=None):
            notification.date_emailed = UTC_NOW
            notification.syncUpdate()

    def newMessage(self, owner=None, subject=None,
                   content=None, parent=None, bugwatch=None):
        """Create a new Message and link it to this bug."""
        msg = Message(
            parent=parent, owner=owner, subject=subject,
            rfc822msgid=make_msgid('malone'))
        MessageChunk(message=msg, content=content, sequence=1)

        bugmsg = self.linkMessage(msg, bugwatch)
        if not bugmsg:
            return

        notify(SQLObjectCreatedEvent(bugmsg, user=owner))

        return bugmsg.message

    def linkMessage(self, message, bugwatch=None, user=None,
                    remote_comment_id=None):
        """See `IBug`."""
        if message not in self.messages:
            if user is None:
                user = message.owner

            result = BugMessage(bug=self, message=message,
                bugwatch=bugwatch, remote_comment_id=remote_comment_id)
            getUtility(IBugWatchSet).fromText(
                message.text_contents, self, user)
            self.findCvesInText(message.text_contents, user)
            return result

    def addWatch(self, bugtracker, remotebug, owner):
        """See `IBug`."""
        # We shouldn't add duplicate bug watches.
        bug_watch = self.getBugWatch(bugtracker, remotebug)
        if bug_watch is not None:
            return bug_watch
        else:
            return BugWatch(
                bug=self, bugtracker=bugtracker,
                remotebug=remotebug, owner=owner)

    def addAttachment(self, owner, file_, comment, filename,
                      is_patch=False, content_type=None, description=None):
        """See `IBug`."""
        filecontent = file_.read()

        if is_patch:
            attach_type = BugAttachmentType.PATCH
            content_type = 'text/plain'
        else:
            attach_type = BugAttachmentType.UNSPECIFIED
            if content_type is None:
                content_type, encoding = guess_content_type(
                    name=filename, body=filecontent)

        filealias = getUtility(ILibraryFileAliasSet).create(
            name=filename, size=len(filecontent),
            file=StringIO(filecontent), contentType=content_type)

        if description:
            title = description
        else:
            title = filename

        if IMessage.providedBy(comment):
            message = comment
        else:
            message = self.newMessage(
                owner=owner, subject=description, content=comment)

        return getUtility(IBugAttachmentSet).create(
            bug=self, filealias=filealias, attach_type=attach_type,
            title=title, message=message, send_notifications=True)

    def hasBranch(self, branch):
        """See `IBug`."""
        branch = BugBranch.selectOneBy(branch=branch, bug=self)

        return branch is not None

    def addBranch(self, branch, registrant, whiteboard=None, status=None):
        """See `IBug`."""
        for bug_branch in shortlist(self.bug_branches):
            if bug_branch.branch == branch:
                return bug_branch
        if status is None:
            status = IBugBranch['status'].default

        bug_branch = BugBranch(
            branch=branch, bug=self, whiteboard=whiteboard, status=status,
            registrant=registrant)
        branch.date_last_modified = UTC_NOW

        notify(SQLObjectCreatedEvent(bug_branch))

        return bug_branch

    def linkCVE(self, cve, user):
        """See `IBug`."""
        if cve not in self.cves:
            bugcve = BugCve(bug=self, cve=cve)
            notify(SQLObjectCreatedEvent(bugcve, user=user))
            return bugcve

    def unlinkCVE(self, cve, user=None):
        """See `IBug`."""
        for cve_link in self.cve_links:
            if cve_link.cve.id == cve.id:
                notify(SQLObjectDeletedEvent(cve_link, user=user))
                BugCve.delete(cve_link.id)
                break

    def findCvesInText(self, text, user):
        """See `IBug`."""
        cves = getUtility(ICveSet).inText(text)
        for cve in cves:
            self.linkCVE(cve, user)

    # Several other classes need to generate lists of bugs, and
    # one thing they often have to filter for is completeness. We maintain
    # this single canonical query string here so that it does not have to be
    # cargo culted into Product, Distribution, ProductSeries etc
    completeness_clause =  """
        BugTask.bug = Bug.id AND """ + BugTask.completeness_clause

    def canBeAQuestion(self):
        """See `IBug`."""
        return (self._getQuestionTargetableBugTask() is not None
            and self.getQuestionCreatedFromBug() is None)

    def _getQuestionTargetableBugTask(self):
        """Return the only bugtask that can be a QuestionTarget, or None.

        Bugs that are also in external bug trackers cannot be converted
        to questions. This is also true for bugs that are being developed.
        None is returned when either of these conditions are true.

        The bugtask is selected by these rules:
        1. It's status is not Invalid.
        2. It is not a conjoined slave.
        Only one bugtask must meet both conditions to be return. When
        zero or many bugtasks match, None is returned.
        """
        # XXX sinzui 2007-10-19:
        # We may want to removed the bugtask.conjoined_master check
        # below. It is used to simplify the task of converting
        # conjoined bugtasks to question--since slaves cannot be
        # directly updated anyway.
        non_invalid_bugtasks = [
            bugtask for bugtask in self.bugtasks
            if (bugtask.status != BugTaskStatus.INVALID
                and bugtask.conjoined_master is None)]
        if len(non_invalid_bugtasks) != 1:
            return None
        [valid_bugtask] = non_invalid_bugtasks
        if valid_bugtask.pillar.official_malone:
            return valid_bugtask
        else:
            return None


    def convertToQuestion(self, person, comment=None):
        """See `IBug`."""
        question = self.getQuestionCreatedFromBug()
        assert question is None, (
            'This bug was already converted to question #%s.' % question.id)
        bugtask = self._getQuestionTargetableBugTask()
        assert bugtask is not None, (
            'A question cannot be created from this bug without a '
            'valid bugtask.')

        bugtask_before_modification = Snapshot(
            bugtask, providing=providedBy(bugtask))
        bugtask.transitionToStatus(BugTaskStatus.INVALID, person)
        edited_fields = ['status']
        if comment is not None:
            bugtask.statusexplanation = comment
            edited_fields.append('statusexplanation')
            self.newMessage(
                owner=person, subject=self.followup_subject(),
                content=comment)
        notify(
            SQLObjectModifiedEvent(
                object=bugtask,
                object_before_modification=bugtask_before_modification,
                edited_fields=edited_fields,
                user=person))

        question_target = IQuestionTarget(bugtask.target)
        question = question_target.createQuestionFromBug(self)

        notify(BugBecameQuestionEvent(self, question, person))
        return question

    def getQuestionCreatedFromBug(self):
        """See `IBug`."""
        for question in self.questions:
            if (question.owner == self.owner
                and question.datecreated == self.datecreated):
                return question
        return None

    def canMentor(self, user):
        """See `ICanBeMentored`."""
        return not (not user or
                    self.is_complete or
                    self.duplicateof is not None or
                    self.isMentor(user) or
                    not user.teams_participated_in)

    def isMentor(self, user):
        """See `ICanBeMentored`."""
        return MentoringOffer.selectOneBy(bug=self, owner=user) is not None

    def offerMentoring(self, user, team):
        """See `ICanBeMentored`."""
        # if an offer exists, then update the team
        mentoringoffer = MentoringOffer.selectOneBy(bug=self, owner=user)
        if mentoringoffer is not None:
            mentoringoffer.team = team
            return mentoringoffer
        # if no offer exists, create one from scratch
        mentoringoffer = MentoringOffer(owner=user, team=team,
            bug=self)
        notify(SQLObjectCreatedEvent(mentoringoffer, user=user))
        return mentoringoffer

    def retractMentoring(self, user):
        """See `ICanBeMentored`."""
        mentoringoffer = MentoringOffer.selectOneBy(bug=self, owner=user)
        if mentoringoffer is not None:
            notify(SQLObjectDeletedEvent(mentoringoffer, user=user))
            MentoringOffer.delete(mentoringoffer.id)

    def getMessageChunks(self):
        """See `IBug`."""
        query = """
            Message.id = MessageChunk.message AND
            BugMessage.message = Message.id AND
            BugMessage.bug = %s
            """ % sqlvalues(self)

        chunks = MessageChunk.select(query,
            clauseTables=["BugMessage", "Message"],
            # XXX: kiko 2006-09-16 bug=60745:
            # There is an issue that presents itself
            # here if we prejoin message.owner: because Message is
            # already in the clauseTables, the SQL generated joins
            # against message twice and that causes the results to
            # break.
            prejoinClauseTables=["Message"],
            # Note the ordering by Message.id here; while datecreated in
            # production is never the same, it can be in the test suite.
            orderBy=["Message.datecreated", "Message.id",
                     "MessageChunk.sequence"])
        chunks = list(chunks)

        # Since we can't prejoin, cache all people at once so we don't
        # have to do it while rendering, which is a big deal for bugs
        # with a million comments.
        owner_ids = set()
        for chunk in chunks:
            if chunk.message.ownerID:
                owner_ids.add(str(chunk.message.ownerID))
        list(Person.select("ID in (%s)" % ",".join(owner_ids)))

        return chunks

    def getNullBugTask(self, product=None, productseries=None,
                    sourcepackagename=None, distribution=None,
                    distroseries=None):
        """See `IBug`."""
        return NullBugTask(bug=self, product=product,
                           productseries=productseries,
                           sourcepackagename=sourcepackagename,
                           distribution=distribution,
                           distroseries=distroseries)

    def addNomination(self, owner, target):
        """See `IBug`."""
        distroseries = None
        productseries = None
        if IDistroSeries.providedBy(target):
            distroseries = target
            target_displayname = target.fullseriesname
            if target.status == DistroSeriesStatus.OBSOLETE:
                raise NominationSeriesObsoleteError(
                    "%s is an obsolete series." % target_displayname)
        else:
            assert IProductSeries.providedBy(target)
            productseries = target
            target_displayname = target.title

        if not self.canBeNominatedFor(target):
            raise NominationError(
                "This bug cannot be nominated for %s." % target_displayname)

        nomination = BugNomination(
            owner=owner, bug=self, distroseries=distroseries,
            productseries=productseries)
        if nomination.canApprove(owner):
            nomination.approve(owner)
        return nomination

    def canBeNominatedFor(self, nomination_target):
        """See `IBug`."""
        try:
            self.getNominationFor(nomination_target)
        except NotFoundError:
            # No nomination exists. Let's see if the bug is already
            # directly targeted to this nomination_target.
            if IDistroSeries.providedBy(nomination_target):
                target_getter = operator.attrgetter("distroseries")
            elif IProductSeries.providedBy(nomination_target):
                target_getter = operator.attrgetter("productseries")
            else:
                raise AssertionError(
                    "Expected IDistroSeries or IProductSeries target. "
                    "Got %r." % nomination_target)

            for task in self.bugtasks:
                if target_getter(task) == nomination_target:
                    # The bug is already targeted at this
                    # nomination_target.
                    return False

            # No nomination or tasks are targeted at this
            # nomination_target.
            return True
        else:
            # The bug is already nominated for this nomination_target.
            return False

    def getNominationFor(self, nomination_target):
        """See `IBug`."""
        if IDistroSeries.providedBy(nomination_target):
            filter_args = dict(distroseriesID=nomination_target.id)
        else:
            filter_args = dict(productseriesID=nomination_target.id)

        nomination = BugNomination.selectOneBy(bugID=self.id, **filter_args)

        if nomination is None:
            raise NotFoundError(
                "Bug #%d is not nominated for %s." % (
                self.id, nomination_target.displayname))

        return nomination

    def getNominations(self, target=None, nominations=None):
        """See `IBug`."""
        # Define the function used as a sort key.
        def by_bugtargetdisplayname(nomination):
            """Return the friendly sort key verson of displayname."""
            return nomination.target.bugtargetdisplayname.lower()

        if nominations is None:
            nominations = BugNomination.selectBy(bugID=self.id)
        if IProduct.providedBy(target):
            filtered_nominations = []
            for nomination in shortlist(nominations):
                if (nomination.productseries and
                    nomination.productseries.product == target):
                    filtered_nominations.append(nomination)
            nominations = filtered_nominations
        elif IDistribution.providedBy(target):
            filtered_nominations = []
            for nomination in shortlist(nominations):
                if (nomination.distroseries and
                    nomination.distroseries.distribution == target):
                    filtered_nominations.append(nomination)
            nominations = filtered_nominations

        return sorted(nominations, key=by_bugtargetdisplayname)

    def getBugWatch(self, bugtracker, remote_bug):
        """See `IBug`."""
        # If the bug tracker is of BugTrackerType.EMAILADDRESS we can
        # never tell if a bug is already being watched upstream, since
        # the remotebug field for such bug watches contains either '' or
        # an RFC822 message ID. In these cases, then, we always return
        # None for the sake of sanity.
        if bugtracker.bugtrackertype == BugTrackerType.EMAILADDRESS:
            return None

        # XXX: BjornT 2006-10-11:
        # This matching is a bit fragile, since bugwatch.remotebug
        # is a user editable text string. We should improve the
        # matching so that for example '#42' matches '42' and so on.
        return BugWatch.selectFirstBy(
            bug=self, bugtracker=bugtracker, remotebug=remote_bug,
            orderBy='id')

    def setStatus(self, target, status, user):
        """See `IBug`."""
        bugtask = self.getBugTask(target)
        if bugtask is None:
            if IProductSeries.providedBy(target):
                bugtask = self.getBugTask(target.product)
            elif ISourcePackage.providedBy(target):
                current_distro_series = target.distribution.currentseries
                current_package = current_distro_series.getSourcePackage(
                    target.sourcepackagename.name)
                if self.getBugTask(current_package) is not None:
                    # The bug is targeted to the current series, don't
                    # fall back on the general distribution task.
                    return None
                distro_package = target.distribution.getSourcePackage(
                    target.sourcepackagename.name)
                bugtask = self.getBugTask(distro_package)
            else:
                return None

        if bugtask is None:
            return None

        if bugtask.conjoined_master is not None:
            bugtask = bugtask.conjoined_master

        if bugtask.status == status:
            return None

        bugtask_before_modification = Snapshot(
            bugtask, providing=providedBy(bugtask))
        bugtask.transitionToStatus(status, user)
        notify(SQLObjectModifiedEvent(
            bugtask, bugtask_before_modification, ['status'], user=user))

        return bugtask

    def setPrivate(self, private, who):
        """See `IBug`.

        We also record who made the change and when the change took
        place.
        """
        if self.private != private:
            if private:
                # Change indirect subscribers into direct subscribers
                # *before* setting private because
                # getIndirectSubscribers() behaves differently when
                # the bug is private.
                for person in self.getIndirectSubscribers():
                    self.subscribe(person, who)

            self.private = private

            if private:
                self.who_made_private = who
                self.date_made_private = UTC_NOW
            else:
                self.who_made_private = None
                self.date_made_private = None

            return True # Changed.
        else:
            return False # Not changed.

    def getBugTask(self, target):
        """See `IBug`."""
        for bugtask in self.bugtasks:
            if bugtask.target == target:
                return bugtask

        return None

    def _getTags(self):
        """Get the tags as a sorted list of strings."""
        tags = [
            bugtag.tag
            for bugtag in BugTag.selectBy(bug=self, orderBy='tag')
            ]
        return tags

    def _setTags(self, tags):
        """Set the tags from a list of strings."""
        # In order to preserve the ordering of the tags, delete all tags
        # and insert the new ones.
        new_tags = set([tag.lower() for tag in tags])
        old_tags = set(self.tags)
        added_tags = new_tags.difference(old_tags)
        removed_tags = old_tags.difference(new_tags)
        for removed_tag in removed_tags:
            tag = BugTag.selectOneBy(bug=self, tag=removed_tag)
            tag.destroySelf()
        for added_tag in added_tags:
            BugTag(bug=self, tag=added_tag)

    tags = property(_getTags, _setTags)


class BugSet:
    """See BugSet."""
    implements(IBugSet)

    valid_bug_name_re = re.compile(r'''^[a-z][a-z0-9\\+\\.\\-]+$''')

    def get(self, bugid):
        """See `IBugSet`."""
        try:
            return Bug.get(bugid)
        except SQLObjectNotFound:
            raise NotFoundError(
                "Unable to locate bug with ID %s." % str(bugid))

    def getByNameOrID(self, bugid):
        """See `IBugSet`."""
        if self.valid_bug_name_re.match(bugid):
            bug = Bug.selectOneBy(name=bugid)
            if bug is None:
                raise NotFoundError(
                    "Unable to locate bug with ID %s." % bugid)
        else:
            try:
                bug = self.get(bugid)
            except ValueError:
                raise NotFoundError(
                    "Unable to locate bug with nickname %s." % bugid)
        return bug

    def searchAsUser(self, user, duplicateof=None, orderBy=None, limit=None):
        """See `IBugSet`."""
        where_clauses = []
        if duplicateof:
            where_clauses.append("Bug.duplicateof = %d" % duplicateof.id)

        admins = getUtility(ILaunchpadCelebrities).admin
        if user:
            if not user.inTeam(admins):
                # Enforce privacy-awareness for logged-in, non-admin users,
                # so that they can only see the private bugs that they're
                # allowed to see.
                where_clauses.append("""
                    (Bug.private = FALSE OR
                     Bug.id in (
                         SELECT Bug.id
                         FROM Bug, BugSubscription, TeamParticipation
                         WHERE Bug.id = BugSubscription.bug AND
                             TeamParticipation.person = %(personid)s AND
                             BugSubscription.person = TeamParticipation.team))
                             """ % sqlvalues(personid=user.id))
        else:
            # Anonymous user; filter to include only public bugs in
            # the search results.
            where_clauses.append("Bug.private = FALSE")

        other_params = {}
        if orderBy:
            other_params['orderBy'] = orderBy
        if limit:
            other_params['limit'] = limit

        return Bug.select(
            ' AND '.join(where_clauses), **other_params)

    def queryByRemoteBug(self, bugtracker, remotebug):
        """See `IBugSet`."""
        bug = Bug.selectFirst("""
                bugwatch.bugtracker = %s AND
                bugwatch.remotebug = %s AND
                bugwatch.bug = bug.id
                """ % sqlvalues(bugtracker.id, str(remotebug)),
                distinct=True,
                clauseTables=['BugWatch'],
                orderBy=['datecreated'])
        return bug

    def createBug(self, bug_params):
        """See `IBugSet`."""
        # Make a copy of the parameter object, because we might modify some
        # of its attribute values below.
        params = Snapshot(
            bug_params, names=[
                "owner", "title", "comment", "description", "msg",
                "datecreated", "security_related", "private",
                "distribution", "sourcepackagename", "binarypackagename",
                "product", "status", "subscribers", "tags",
                "subscribe_reporter"])

        if not (params.comment or params.description or params.msg):
            raise AssertionError(
                'Method createBug requires a comment, msg, or description.')

        # make sure we did not get TOO MUCH information
        assert params.comment is None or params.msg is None, (
            "Expected either a comment or a msg, but got both.")
        if params.product and params.product.private_bugs:
            # If the private_bugs flag is set on a product, then
            # force the new bug report to be private.
            params.private = True

        # Store binary package name in the description, because
        # storing it as a separate field was a maintenance burden to
        # developers.
        if params.binarypackagename:
            params.comment = "Binary package hint: %s\n\n%s" % (
                params.binarypackagename.name, params.comment)

        # Create the bug comment if one was given.
        if params.comment:
            rfc822msgid = make_msgid('malonedeb')
            params.msg = Message(
                subject=params.title, distribution=params.distribution,
                rfc822msgid=rfc822msgid, owner=params.owner)
            MessageChunk(
                message=params.msg, sequence=1, content=params.comment,
                blob=None)

        # Extract the details needed to create the bug and optional msg.
        if not params.description:
            params.description = params.msg.text_contents

        if not params.datecreated:
            params.datecreated = UTC_NOW

        extra_params = {}
        if params.private:
            # We add some auditing information. After bug creation
            # time these attributes are updated by Bug.setPrivate().
            extra_params.update(
                date_made_private=params.datecreated,
                who_made_private=params.owner)

        bug = Bug(
            title=params.title, description=params.description,
            private=params.private, owner=params.owner,
            datecreated=params.datecreated,
            security_related=params.security_related,
            **extra_params)

        if params.subscribe_reporter:
            bug.subscribe(params.owner, params.owner)
        if params.tags:
            bug.tags = params.tags

        if params.security_related:
            assert params.private, (
                "A security related bug should always be private by default.")
            if params.product:
                context = params.product
            else:
                context = params.distribution

            if context.security_contact:
                bug.subscribe(context.security_contact, params.owner)
            else:
                bug.subscribe(context.owner, params.owner)
        # XXX: ElliotMurphy 2007-06-14: If we ever allow filing private
        # non-security bugs, this test might be simplified to checking
        # params.private.
        elif params.product and params.product.private_bugs:
            # Subscribe the bug supervisor to all bugs,
            # because all their bugs are private by default
            # otherwise only subscribe the bug reporter by default.
            if params.product.bug_supervisor:
                bug.subscribe(params.product.bug_supervisor, params.owner)
            else:
                bug.subscribe(params.product.owner, params.owner)
        else:
            # nothing to do
            pass

        # Subscribe other users.
        for subscriber in params.subscribers:
            bug.subscribe(subscriber, params.owner)

        # Link the bug to the message.
        BugMessage(bug=bug, message=params.msg)

        # Create the task on a product if one was passed.
        if params.product:
            BugTaskSet().createTask(
                bug=bug, product=params.product, owner=params.owner,
                status=params.status)

        # Create the task on a source package name if one was passed.
        if params.distribution:
            BugTaskSet().createTask(
                bug=bug, distribution=params.distribution,
                sourcepackagename=params.sourcepackagename,
                owner=params.owner, status=params.status)

        return bug
