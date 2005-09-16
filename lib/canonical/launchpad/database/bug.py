# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Launchpad bug-related database table classes."""

__metaclass__ = type
__all__ = ['Bug', 'BugSet']

from sets import Set
from email.Utils import make_msgid

from zope.interface import implements
from zope.exceptions import NotFoundError
from zope.event import notify

from sqlobject import ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin
from sqlobject import SQLObjectNotFound

from canonical.launchpad.interfaces import IBug, IBugSet
from canonical.launchpad.helpers import contactEmailAddresses
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW, DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.lp import dbschema
from canonical.launchpad.database.bugcve import BugCve
from canonical.launchpad.database.bugset import BugSetBase
from canonical.launchpad.database.message import (
    Message, MessageChunk)
from canonical.launchpad.database.bugmessage import BugMessage
from canonical.launchpad.database.bugtask import BugTask, bugtask_sort_key
from canonical.launchpad.database.bugwatch import BugWatch
from canonical.launchpad.database.bugsubscription import BugSubscription
from canonical.launchpad.database.maintainership import Maintainership
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

                if task.product is not None:
                    owner = task.product.owner
                    emails.update(contactEmailAddresses(owner))
                else:
                    if task.sourcepackagename is not None:
                        if task.distribution is not None:
                            distribution = task.distribution
                        else:
                            distribution = task.distrorelease.distribution

                        maintainership = Maintainership.selectOneBy(
                            sourcepackagenameID = task.sourcepackagename.id,
                            distributionID = distribution.id)

                        if maintainership is not None:
                            maintainer = maintainership.maintainer
                            emails.update(contactEmailAddresses(maintainer))

        emails.update(contactEmailAddresses(self.owner))
        emails = list(emails)
        emails.sort()
        return emails

    # messages
    def newMessage(self, owner=None, subject=None, content=None,
        parent=None):
        """Create a new Message and link it to this ticket."""
        msg = Message(parent=parent, owner=owner,
            rfc822msgid=make_msgid('malone'), subject=subject)
        chunk = MessageChunk(messageID=msg.id, content=content, sequence=1)
        bugmsg = BugMessage(bug=self, message=msg)
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

    def findCvesInText(self, bug, text):
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

    def search(self, duplicateof=None):
        """See canonical.launchpad.interfaces.bug.IBugSet."""
        return Bug.selectBy(duplicateofID=duplicateof.id)

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
        """Create a bug and return it.

        Things to note when using this factory:

          * if no description is passed, the comment will be used as the
            description

          * if summary is not passed then the summary will be the
            first sentence of the description

          * the submitter will be subscribed to the bug

          * if either product or distribution is specified, an appropiate
            bug task will be created

        """
        # make sure that the factory has been passed enough information
        if comment is description is msg is None:
            raise ValueError(
                'createBug requires a comment, msg, or description')

        # make sure we did not get TOO MUCH information
        assert (comment is None or msg is None), "Too much information"

        # create the bug comment if one was given
        if comment:
            rfc822msgid = make_msgid('malonedeb')
            msg = Message(subject=title, distribution=distribution,
                rfc822msgid=rfc822msgid, owner=owner)
            chunk = MessageChunk(messageID=msg.id, sequence=1,
                content=comment, blobID=None)

        # extract the details needed to create the bug and optional msg
        if not description:
            description = msg.contents

        if not datecreated:
            datecreated = UTC_NOW

        bug = Bug(
            title=title, summary=summary,
            description=description, private=private,
            owner=owner.id, datecreated=datecreated)

        sub = BugSubscription(person=owner.id, bug=bug.id)

        # link the bug to the message
        bugmsg = BugMessage(bug=bug, message=msg)

        # create the task on a product if one was passed
        if product:
            BugTask(bug=bug, product=product, owner=owner)

        # create the task on a source package name if one was passed
        if distribution:
            task = BugTask(
                    bug=bug,
                    distribution=distribution,
                    sourcepackagename=sourcepackagename,
                    binarypackagename=binarypackagename,
                    owner=owner)

        return bug


