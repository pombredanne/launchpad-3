# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Launchpad bug-related database table classes."""

__metaclass__ = type
__all__ = ['Bug', 'BugSet']

from sets import Set
from email.Utils import make_msgid

from zope.component import getUtility
from zope.event import notify
from zope.interface import implements

from sqlobject import ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin
from sqlobject import SQLObjectNotFound

from canonical.launchpad.interfaces import (
    IBug, IBugSet, ICveSet, NotFoundError, ILaunchpadCelebrities)
from canonical.launchpad.helpers import contactEmailAddresses
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW, DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.database.bugcve import BugCve
from canonical.launchpad.database.bugset import BugSetBase
from canonical.launchpad.database.message import (
    Message, MessageChunk)
from canonical.launchpad.database.bugmessage import BugMessage
from canonical.launchpad.database.bugtask import BugTask, bugtask_sort_key
from canonical.launchpad.database.bugwatch import BugWatch
from canonical.launchpad.database.bugsubscription import BugSubscription
from canonical.launchpad.event.sqlobjectevent import (
    SQLObjectCreatedEvent, SQLObjectDeletedEvent)

from zope.i18n import MessageIDFactory
_ = MessageIDFactory("launchpad")


class Bug(SQLBase):
    """A bug."""

    implements(IBug)

    _defaultOrder = '-id'

    # db field names
    name = StringCol(unique=True, default=None)
    title = StringCol(notNull=True)
    summary = StringCol(notNull=False, default=None)
    description = StringCol(notNull=False,
                            default=None)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    duplicateof = ForeignKey(
        dbName='duplicateof', foreignKey='Bug', default=None)
    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
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

    # useful Joins
    activity = MultipleJoin('BugActivity', joinColumn='bug', orderBy='id')
    messages = RelatedJoin('Message', joinColumn='bug',
                           otherColumn='message',
                           intermediateTable='BugMessage',
                           orderBy='datecreated')
    productinfestations = MultipleJoin(
            'BugProductInfestation', joinColumn='bug', orderBy='id')
    packageinfestations = MultipleJoin(
            'BugPackageInfestation', joinColumn='bug', orderBy='id')
    watches = MultipleJoin('BugWatch', joinColumn='bug')
    externalrefs = MultipleJoin(
            'BugExternalRef', joinColumn='bug', orderBy='id')
    cves = RelatedJoin('Cve', intermediateTable='BugCve',
        orderBy='sequence', joinColumn='bug', otherColumn='cve')
    cve_links = MultipleJoin('BugCve', joinColumn='bug', orderBy='id')
    subscriptions = MultipleJoin(
            'BugSubscription', joinColumn='bug', orderBy='id')
    duplicates = MultipleJoin('Bug', joinColumn='duplicateof', orderBy='id')
    attachments = MultipleJoin('BugAttachment', joinColumn='bug', orderBy='id')
    specifications = RelatedJoin('Specification', joinColumn='bug',
        otherColumn='specification', intermediateTable='SpecificationBug',
        orderBy='-datecreated')
    tickets = RelatedJoin('Ticket', joinColumn='bug',
        otherColumn='ticket', intermediateTable='TicketBug',
        orderBy='-datecreated')

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
        bs = BugSubscription.selectBy(bugID=self.id, personID=person.id)
        return bool(bs.count())

    def notificationRecipientAddresses(self):
        """See canonical.launchpad.interfaces.IBug."""
        emails = Set()
        for subscription in self.subscriptions:
            emails.update(contactEmailAddresses(subscription.person))

        if not self.private:
            # Collect implicit subscriptions. This only happens on
            # public bugs.
            for task in self.bugtasks:
                if task.assignee is not None:
                    emails.update(contactEmailAddresses(task.assignee))

        emails = list(emails)
        emails.sort()
        return emails

    # messages
    def newMessage(self, owner=None, subject=None, content=None,
        parent=None):
        """Create a new Message and link it to this ticket."""
        msg = Message(parent=parent, owner=owner,
            rfc822msgid=make_msgid('malone'), subject=subject)
        MessageChunk(messageID=msg.id, content=content, sequence=1)
        bugmsg = BugMessage(bug=self, message=msg)
        notify(SQLObjectCreatedEvent(bugmsg, user=owner))
        return msg

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


class BugSet(BugSetBase):
    implements(IBugSet)

    def __iter__(self):
        """See canonical.launchpad.interfaces.bug.IBugSet."""
        for row in Bug.select():
            yield row

    def get(self, bugid):
        """See canonical.launchpad.interfaces.bug.IBugSet."""
        try:
            return Bug.get(bugid)
        except SQLObjectNotFound:
            raise NotFoundError(
                "Unable to locate bug with ID %s" % str(bugid))

    def searchAsUser(self, user, duplicateof=None, orderBy=None, limit=None):
        """See canonical.launchpad.interfaces.bug.IBugSet."""
        where_clauses = []
        if duplicateof:
            where_clauses.append("Bug.duplicateof = %d" % duplicateof.id)

        admins = getUtility(ILaunchpadCelebrities).admin
        if user:
            if not user.inTeam(admins):
                # Enforce privacy-awareness for logged-in, non-admin users, so that
                # they can only see the private bugs that they're allowed to see.
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

        # XXX, Brad Bollenbach, 2005-10-12: The following if/else appears to be
        # necessary due to sqlobject appearing to generate crap SQL when an
        # empty WHERE clause arg is passed. Filed the bug here:
        #
        # https://launchpad.net/products/launchpad/+bug/3096
        if where_clauses:
            return Bug.select(
                ' AND '.join(where_clauses), **other_params)
        else:
            return Bug.select(**other_params)

    def queryByRemoteBug(self, bugtracker, remotebug):
        """See IBugSet."""
        buglist = Bug.select("""
                bugwatch.bugtracker = %s AND
                bugwatch.remotebug = %s AND
                bugwatch.bug = bug.id
                """ % sqlvalues(bugtracker.id, str(remotebug)),
                distinct=True,
                clauseTables=['BugWatch'],
                orderBy=['datecreated'])
        # ths is weird, but it works around a bug in sqlobject which does
        # not like slicing buglist (will give a warning if you try to show
        # buglist[0] for example
        for item in buglist:
            return item
        return None

    def createBug(self, distribution=None, sourcepackagename=None,
        binarypackagename=None, product=None, comment=None,
        description=None, msg=None, summary=None, datecreated=None,
        title=None, private=False, owner=None):
        """See IBugSet."""
        # Make sure that the factory has been passed enough information.
        if comment is description is msg is None:
            raise AssertionError(
                'createBug requires a comment, msg, or description')

        # make sure we did not get TOO MUCH information
        assert (comment is None or msg is None), "Too much information"

        # Create the bug comment if one was given.
        if comment:
            rfc822msgid = make_msgid('malonedeb')
            msg = Message(subject=title, distribution=distribution,
                rfc822msgid=rfc822msgid, owner=owner)
            MessageChunk(
                messageID=msg.id, sequence=1, content=comment, blobID=None)

        # Extract the details needed to create the bug and optional msg.
        if not description:
            description = msg.contents

        if not datecreated:
            datecreated = UTC_NOW

        bug = Bug(
            title=title, summary=summary,
            description=description, private=private,
            owner=owner.id, datecreated=datecreated)

        bug.subscribe(owner)

        # Link the bug to the message.
        BugMessage(bug=bug, message=msg)

        # Create the task on a product if one was passed.
        if product:
            BugTask(bug=bug, product=product, owner=owner)

            # If a product bug contact has been provided, subscribe that contact
            # to all public bugs. Otherwise subscribe the product owner to all
            # public bugs.
            if product.bugcontact:
                if not bug.private:
                    bug.subscribe(product.bugcontact)
            else:
                if not bug.private:
                    bug.subscribe(product.owner)

        # Create the task on a source package name if one was passed.
        if distribution:
            BugTask(
                bug=bug,
                distribution=distribution,
                sourcepackagename=sourcepackagename,
                binarypackagename=binarypackagename,
                owner=owner)

            # If a distribution bug contact has been provided, subscribe that
            # contact to all public bugs.
            if distribution.bugcontact and not bug.private:
                bug.subscribe(distribution.bugcontact)

            # Subscribe package bug contacts to public bugs, if package
            # information was provided.
            if sourcepackagename:
                package = distribution.getSourcePackage(sourcepackagename.name)
                if package.bugcontacts and not bug.private:
                    for pkg_bugcontact in package.bugcontacts:
                        bug.subscribe(pkg_bugcontact.bugcontact)

        return bug
