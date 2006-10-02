# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Launchpad bug-related database table classes."""

__metaclass__ = type
__all__ = ['Bug', 'BugSet', 'get_bug_tags', 'get_bug_tags_open_count']

import operator
import re
from cStringIO import StringIO
from email.Utils import make_msgid

from zope.app.content_types import guess_content_type
from zope.component import getUtility
from zope.event import notify
from zope.interface import implements

from sqlobject import ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import SQLMultipleJoin, SQLRelatedJoin
from sqlobject import SQLObjectNotFound

from canonical.launchpad.interfaces import (
    IBug, IBugSet, ICveSet, NotFoundError, ILaunchpadCelebrities,
    IDistroBugTask, IDistroReleaseBugTask, ILibraryFileAliasSet,
    IBugAttachmentSet, IMessage, IUpstreamBugTask,
    UNRESOLVED_BUGTASK_STATUSES)
from canonical.launchpad.helpers import contactEmailAddresses, shortlist
from canonical.database.sqlbase import cursor, SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW, DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.database.bugbranch import BugBranch
from canonical.launchpad.database.bugcve import BugCve
from canonical.launchpad.database.bugnotification import BugNotification
from canonical.launchpad.database.message import (
    MessageSet, Message, MessageChunk)
from canonical.launchpad.database.bugmessage import BugMessage
from canonical.launchpad.database.bugtask import (
    BugTask, BugTaskSet, bugtask_sort_key, get_bug_privacy_filter)
from canonical.launchpad.database.bugwatch import BugWatch
from canonical.launchpad.database.bugsubscription import BugSubscription
from canonical.launchpad.event.sqlobjectevent import (
    SQLObjectCreatedEvent, SQLObjectDeletedEvent)
from canonical.launchpad.webapp.snapshot import Snapshot
from canonical.lp.dbschema import BugAttachmentType


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


class Bug(SQLBase):
    """A bug."""

    implements(IBug)

    _defaultOrder = '-id'

    # db field names
    name = StringCol(unique=True, default=None)
    title = StringCol(notNull=True)
    description = StringCol(notNull=False,
                            default=None)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    duplicateof = ForeignKey(
        dbName='duplicateof', foreignKey='Bug', default=None)
    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    date_last_updated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    communityscore = IntCol(dbName='communityscore', notNull=True, default=0)
    communitytimestamp = UtcDateTimeCol(dbName='communitytimestamp',
                                        notNull=True, default=DEFAULT)
    hits = IntCol(dbName='hits', notNull=True, default=0)
    hitstimestamp = UtcDateTimeCol(dbName='hitstimestamp', notNull=True,
                                   default=DEFAULT)
    activityscore = IntCol(dbName='activityscore', notNull=True, default=0)
    activitytimestamp = UtcDateTimeCol(dbName='activitytimestamp',
                                       notNull=True, default=DEFAULT)
    private = BoolCol(notNull=True, default=False)
    security_related = BoolCol(notNull=True, default=False)

    # useful Joins
    activity = SQLMultipleJoin('BugActivity', joinColumn='bug', orderBy='id')
    messages = SQLRelatedJoin('Message', joinColumn='bug',
                           otherColumn='message',
                           intermediateTable='BugMessage',
                           prejoins=['owner'],
                           orderBy='datecreated')
    productinfestations = SQLMultipleJoin(
            'BugProductInfestation', joinColumn='bug', orderBy='id')
    packageinfestations = SQLMultipleJoin(
            'BugPackageInfestation', joinColumn='bug', orderBy='id')
    watches = SQLMultipleJoin(
        'BugWatch', joinColumn='bug', orderBy=['bugtracker', 'remotebug'])
    externalrefs = SQLMultipleJoin(
            'BugExternalRef', joinColumn='bug', orderBy='id')
    cves = SQLRelatedJoin('Cve', intermediateTable='BugCve',
        orderBy='sequence', joinColumn='bug', otherColumn='cve')
    cve_links = SQLMultipleJoin('BugCve', joinColumn='bug', orderBy='id')
    # XXX: why is subscriptions ordered by ID? -- kiko, 2006-09-23
    subscriptions = SQLMultipleJoin(
            'BugSubscription', joinColumn='bug', orderBy='id',
            prejoins=["person"])
    duplicates = SQLMultipleJoin('Bug', joinColumn='duplicateof', orderBy='id')
    attachments = SQLMultipleJoin('BugAttachment', joinColumn='bug',
        orderBy='id', prejoins=['libraryfile'])
    specifications = SQLRelatedJoin('Specification', joinColumn='bug',
        otherColumn='specification', intermediateTable='SpecificationBug',
        orderBy='-datecreated')
    tickets = SQLRelatedJoin('Ticket', joinColumn='bug',
        otherColumn='ticket', intermediateTable='TicketBug',
        orderBy='-datecreated')
    bug_branches = SQLMultipleJoin('BugBranch', joinColumn='bug', orderBy='id')

    @property
    def displayname(self):
        """See IBug."""
        dn = 'Bug #%d' % self.id
        if self.name:
            dn += ' ('+self.name+')'
        return dn

    @property
    def bugtasks(self):
        """See IBug."""
        result = BugTask.selectBy(bug=self)
        result.prejoin(["assignee"])
        return sorted(result, key=bugtask_sort_key)

    @property
    def initial_message(self):
        """See IBug."""
        messages = sorted(self.messages, key=lambda ob: ob.id)
        return messages[0]

    def followup_subject(self):
        return 'Re: '+ self.title

    def subscribe(self, person):
        """See canonical.launchpad.interfaces.IBug."""
        # first look for an existing subscription
        for sub in self.subscriptions:
            if sub.person.id == person.id:
                return sub

        return BugSubscription(bug=self, person=person)

    def unsubscribe(self, person):
        """See canonical.launchpad.interfaces.IBug."""
        for sub in self.subscriptions:
            if sub.person.id == person.id:
                BugSubscription.delete(sub.id)
                return

    def isSubscribed(self, person):
        """See canonical.launchpad.interfaces.IBug."""
        if person is None:
            return False

        bs = BugSubscription.selectBy(bug=self, person=person)
        return bool(bs.count())

    def getDirectSubscribers(self):
        """See canonical.launchpad.interfaces.IBug."""
        return [sub.person for sub in self.subscriptions]

    def getIndirectSubscribers(self):
        """See canonical.launchpad.interfaces.IBug."""
        if self.private:
            return []

        indirect_subscribers = set()

        for bugtask in self.bugtasks:
            # Assignees are indirect subscribers.
            if bugtask.assignee:
                indirect_subscribers.add(bugtask.assignee)

            # Bug contacts are indirect subscribers.
            if (IDistroBugTask.providedBy(bugtask) or
                IDistroReleaseBugTask.providedBy(bugtask)):
                if bugtask.distribution is not None:
                    distribution = bugtask.distribution
                else:
                    distribution = bugtask.distrorelease.distribution

                if distribution.bugcontact:
                    indirect_subscribers.add(distribution.bugcontact)

                if bugtask.sourcepackagename:
                    sourcepackage = distribution.getSourcePackage(
                        bugtask.sourcepackagename)
                    indirect_subscribers.update(
                        pbc.bugcontact for pbc in sourcepackage.bugcontacts)
            else:
                assert IUpstreamBugTask.providedBy(bugtask)
                product = bugtask.product
                if product.bugcontact:
                    indirect_subscribers.add(product.bugcontact)
                else:
                    indirect_subscribers.add(product.owner)

        # Subscribers, whether direct or indirect, from duplicate bugs become
        # indirect subscribers of this bug.
        for dupe in self.duplicates:
            indirect_subscribers.update(dupe.getDirectSubscribers())
            indirect_subscribers.update(dupe.getIndirectSubscribers())

        # Direct subscriptions always take precedence over indirect
        # subscriptions.
        direct_subscribers = set(self.getDirectSubscribers())
        return sorted(indirect_subscribers.difference(direct_subscribers),
                      key=operator.attrgetter('id'))

    def notificationRecipientAddresses(self):
        """See canonical.launchpad.interfaces.IBug."""
        emails = set()
        for direct_subscriber in self.getDirectSubscribers():
            emails.update(contactEmailAddresses(direct_subscriber))

        if not self.private:
            for indirect_subscriber in self.getIndirectSubscribers():
                emails.update(contactEmailAddresses(indirect_subscriber))
        else:
            assert self.getIndirectSubscribers() == [], (
                "Indirect subscribers found on private bug. "
                "A private bug should never have implicit subscribers!")

        return sorted(emails)

    def addChangeNotification(self, text, person, when=None):
        """See IBug."""
        if when is None:
            when = UTC_NOW
        message = MessageSet().fromText(
            self.followup_subject(), text, owner=person, datecreated=when)
        BugNotification(
            bug=self, is_comment=False, message=message, date_emailed=None)

    def addCommentNotification(self, message):
        """See IBug."""
        BugNotification(
            bug=self, is_comment=True, message=message, date_emailed=None)

    def newMessage(self, owner=None, subject=None, content=None, parent=None):
        """Create a new Message and link it to this bug."""
        msg = Message(
            parent=parent, owner=owner, subject=subject,
            rfc822msgid=make_msgid('malone'))
        MessageChunk(message=msg, content=content, sequence=1)

        bugmsg = BugMessage(bug=self, message=msg)

        notify(SQLObjectCreatedEvent(bugmsg, user=owner))

        return bugmsg.message

    def linkMessage(self, message):
        """See IBug."""
        if message not in self.messages:
            return BugMessage(bug=self, message=message)

    def addWatch(self, bugtracker, remotebug, owner):
        """See IBug."""
        # run through the existing watches and try to find an existing watch
        # that matches... and return that
        for watch in self.watches:
            if (watch.bugtracker == bugtracker and
                watch.remotebug == remotebug):
                return watch
        # ok, we need a new one
        return BugWatch(bug=self, bugtracker=bugtracker,
            remotebug=remotebug, owner=owner)

    def addAttachment(self, owner, file_, description, comment, filename,
                      is_patch=False):
        """See IBug."""
        filecontent = file_.read()

        if is_patch:
            attach_type = BugAttachmentType.PATCH
            content_type = 'text/plain'
        else:
            attach_type = BugAttachmentType.UNSPECIFIED
            content_type, encoding = guess_content_type(
                name=filename, body=filecontent)

        filealias = getUtility(ILibraryFileAliasSet).create(
            name=filename, size=len(filecontent),
            file=StringIO(filecontent), contentType=content_type)

        if description:
            title = description
        else:
            title = self.followup_subject()

        if IMessage.providedBy(comment):
            message = comment
        else:
            message = self.newMessage(
                owner=owner, subject=description, content=comment)

        attachment = getUtility(IBugAttachmentSet).create(
            bug=self, filealias=filealias, attach_type=attach_type,
            title=title, message=message)
        notify(SQLObjectCreatedEvent(attachment))
        return attachment

    def hasBranch(self, branch):
        """See canonical.launchpad.interfaces.IBug."""
        branch = BugBranch.selectOneBy(branch=branch, bug=self)

        return branch is not None

    def addBranch(self, branch, whiteboard=None):
        """See canonical.launchpad.interfaces.IBug."""
        for bug_branch in shortlist(self.bug_branches):
            if bug_branch.branch == branch:
                return bug_branch

        bug_branch = BugBranch(
            branch=branch, bug=self, whiteboard=whiteboard)

        notify(SQLObjectCreatedEvent(bug_branch))

        return bug_branch

    def linkCVE(self, cve, user=None):
        """See IBug."""
        if cve not in self.cves:
            bugcve = BugCve(bug=self, cve=cve)
            notify(SQLObjectCreatedEvent(bugcve, user=user))
            return bugcve

    def unlinkCVE(self, cve, user=None):
        """See IBug."""
        for cve_link in self.cve_links:
            if cve_link.cve.id == cve.id:
                notify(SQLObjectDeletedEvent(cve_link, user=user))
                BugCve.delete(cve_link.id)
                break

    def findCvesInText(self, text):
        """See IBug."""
        cves = getUtility(ICveSet).inText(text)
        for cve in cves:
            self.linkCVE(cve)

    def getMessageChunks(self):
        """See IBug."""
        chunks = MessageChunk.select("""
            Message.id = MessageChunk.message AND
            BugMessage.message = Message.id AND
            BugMessage.bug = %s
            """ % sqlvalues(self),
            clauseTables=["BugMessage", "Message"],
            # XXX: See bug 60745. There is an issue that presents itself
            # here if we prejoin message.owner: because Message is
            # already in the clauseTables, the SQL generated joins
            # against message twice and that causes the results to
            # break. -- kiko, 2006-09-16
            prejoinClauseTables=["Message"],
            # Note the ordering by Message.id here; while datecreated in
            # production is never the same, it can be in the test suite.
            orderBy=["Message.datecreated", "Message.id",
                     "MessageChunk.sequence"])
        return chunks

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
    implements(IBugSet)

    valid_bug_name_re = re.compile(r'''^[a-z][a-z0-9\\+\\.\\-]+$''')

    def get(self, bugid):
        """See canonical.launchpad.interfaces.bug.IBugSet."""
        try:
            return Bug.get(bugid)
        except SQLObjectNotFound:
            raise NotFoundError(
                "Unable to locate bug with ID %s" % str(bugid))

    def getByNameOrID(self, bugid):
        """See canonical.launchpad.interfaces.bug.IBugSet."""
        if self.valid_bug_name_re.match(bugid):
            bug = Bug.selectOneBy(name=bugid)
            if bug is None:
                raise NotFoundError(
                    "Unable to locate bug with ID %s" % bugid)
        else:
            try:
                bug = self.get(bugid)
            except ValueError:
                raise NotFoundError(
                    "Unable to locate bug with nickname %s" % bugid)
        return bug

    def searchAsUser(self, user, duplicateof=None, orderBy=None, limit=None):
        """See canonical.launchpad.interfaces.bug.IBugSet."""
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
        """See IBugSet."""
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
        """See IBugSet."""
        # Make a copy of the parameter object, because we might modify some of
        # its attribute values below.
        params = Snapshot(
            bug_params, names=[
                "owner", "title", "comment", "description", "msg",
                "datecreated", "security_related", "private",
                "distribution", "sourcepackagename", "binarypackagename",
                "product", "status", "subscribers"])

        if not (params.comment or params.description or params.msg):
            raise AssertionError(
                'createBug requires a comment, msg, or description')

        # make sure we did not get TOO MUCH information
        assert params.comment is None or params.msg is None, (
            "Expected either a comment or a msg, but got both")

        celebs = getUtility(ILaunchpadCelebrities)
        if params.product == celebs.landscape:
            # Landscape bugs are always private, because details of the
            # project, like bug reports, are not yet meant to be
            # publically disclosed.
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

        bug = Bug(
            title=params.title, description=params.description,
            private=params.private, owner=params.owner,
            datecreated=params.datecreated,
            security_related=params.security_related)

        bug.subscribe(params.owner)

        if params.product == celebs.landscape:
            # Subscribe the Landscape bugcontact to all Landscape bugs,
            # because all their bugs are private by default, and so will
            # otherwise only subscribe the bug reporter by default.
            bug.subscribe(celebs.landscape.bugcontact)

        if params.security_related:
            assert params.private, (
                "A security related bug should always be private by default")
            if params.product:
                context = params.product
            else:
                context = params.distribution

            if context.security_contact:
                bug.subscribe(context.security_contact)
            else:
                bug.subscribe(context.owner)

        # Subscribe other users.
        for subscriber in params.subscribers:
            bug.subscribe(subscriber)

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

