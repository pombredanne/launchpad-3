# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Launchpad bug-related database table classes."""

__metaclass__ = type
__all__ = ['Bug', 'BugSet', 'get_bug_tags']

from cStringIO import StringIO
from email.Utils import make_msgid
import re
from sets import Set

from zope.app.content_types import guess_content_type
from zope.component import getUtility
from zope.event import notify
from zope.interface import implements

from sqlobject import ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import SQLMultipleJoin, SQLRelatedJoin
from sqlobject import SQLObjectNotFound

from canonical.launchpad.interfaces import (
    IBug, IBugSet, ICveSet, NotFoundError, ILaunchpadCelebrities,
    IUpstreamBugTask, IDistroBugTask, IDistroReleaseBugTask,
    ILibraryFileAlias, ILibraryFileAliasSet, IBugMessageSet,
    ILaunchBag, IBugAttachmentSet, IMessage)
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
    BugTask, BugTaskSet, bugtask_sort_key)
from canonical.launchpad.database.bugwatch import BugWatch
from canonical.launchpad.database.bugsubscription import BugSubscription
from canonical.launchpad.event.sqlobjectevent import (
    SQLObjectCreatedEvent, SQLObjectDeletedEvent)
from canonical.launchpad.helpers import shortlist
from canonical.lp.dbschema import BugAttachmentType


def get_bug_tags(context_clause):
    """Return all the bug tags as a list of strings.

    context_clause is a SQL condition clause, limiting the tags to a
    specific context.
    """
    cur = cursor()
    cur.execute(
        "SELECT DISTINCT BugTag.tag FROM BugTag, BugTask WHERE"
        " BugTag.bug = BugTask.bug AND %s" % context_clause)
    return shortlist([row[0] for row in cur.fetchall()])

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
    subscriptions = SQLMultipleJoin(
            'BugSubscription', joinColumn='bug', orderBy='id')
    duplicates = SQLMultipleJoin('Bug', joinColumn='duplicateof', orderBy='id')
    attachments = SQLMultipleJoin('BugAttachment', joinColumn='bug', 
        orderBy='id')
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
        result = BugTask.select("bug=%s" % sqlvalues(self.id))
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

        bs = BugSubscription.selectBy(bugID=self.id, personID=person.id)
        return bool(bs.count())

    def getDirectSubscribers(self):
        """See canonical.launchpad.interfaces.IBug."""
        direct_subscribers = []

        for subscription in self.subscriptions:
            direct_subscribers.append(subscription.person)

        return direct_subscribers

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
        return list(indirect_subscribers.difference(direct_subscribers))

    def notificationRecipientAddresses(self):
        """See canonical.launchpad.interfaces.IBug."""
        emails = Set()
        for direct_subscriber in self.getDirectSubscribers():
            emails.update(contactEmailAddresses(direct_subscriber))


        if not self.private:
            for indirect_subscriber in self.getIndirectSubscribers():
                emails.update(contactEmailAddresses(indirect_subscriber))
        else:
            assert self.getIndirectSubscribers() == [], (
                "Indirect subscribers found on private bug. "
                "A private bug should never have implicit subscribers!")

        return list(emails)

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
        MessageChunk(messageID=msg.id, content=content, sequence=1)

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

        return getUtility(IBugAttachmentSet).create(
            bug=self, filealias=filealias, attach_type=attach_type,
            title=title, message=message)

    def hasBranch(self, branch):
        """See canonical.launchpad.interfaces.IBug."""
        branch = BugBranch.selectOneBy(branchID=branch.id, bugID=self.id)

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

    def _getTags(self):
        """Get the tags as a list of strings."""
        tags = [
            bugtag.tag
            for bugtag in BugTag.selectBy(
                bugID=self.id, orderBy='id')
            ]
        return tags

    def _setTags(self, tags):
        """Set the tags from a list of strings."""
        # In order to preserve the ordering of the tags, delete all tags
        # and insert the new ones.
        for old_tag in self.tags:
            tag = BugTag.selectFirstBy(
                bugID=self.id, tag=old_tag, orderBy="id")
            tag.destroySelf()
        for new_tag in tags:
            BugTag(bug=self, tag=new_tag.lower())


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

    def createBug(self, distribution=None, sourcepackagename=None,
                  binarypackagename=None, product=None, comment=None,
                  description=None, msg=None, datecreated=None, title=None,
                  security_related=False, private=False, owner=None):
        """See IBugSet."""
        if comment is description is msg is None:
            raise AssertionError(
                'createBug requires a comment, msg, or description')

        # make sure we did not get TOO MUCH information
        assert comment is None or msg is None, (
            "Expected either a comment or a msg, but got both")

        # Store binary package name in the description, because
        # storing it as a separate field was a maintenance burden to
        # developers.
        if binarypackagename:
            comment = "Binary package hint: %s\n\n%s" % (
                binarypackagename.name, comment)

        # Create the bug comment if one was given.
        if comment:
            rfc822msgid = make_msgid('malonedeb')
            msg = Message(subject=title, distribution=distribution,
                rfc822msgid=rfc822msgid, owner=owner)
            MessageChunk(
                messageID=msg.id, sequence=1, content=comment, blobID=None)

        # Extract the details needed to create the bug and optional msg.
        if not description:
            description = msg.text_contents

        if not datecreated:
            datecreated = UTC_NOW

        bug = Bug(
            title=title, description=description, private=private,
            owner=owner.id, datecreated=datecreated,
            security_related=security_related)

        bug.subscribe(owner)
        # Subscribe the security contact, for security-related bugs.
        if security_related:
            if product and product.security_contact:
                bug.subscribe(product.security_contact)
            elif distribution and distribution.security_contact:
                bug.subscribe(distribution.security_contact)

        # Link the bug to the message.
        BugMessage(bug=bug, message=msg)

        # Create the task on a product if one was passed.
        if product:
            BugTaskSet().createTask(bug=bug, product=product, owner=owner)

        # Create the task on a source package name if one was passed.
        if distribution:
            BugTaskSet().createTask(
                bug=bug, distribution=distribution,
                sourcepackagename=sourcepackagename,
                owner=owner)

        return bug
