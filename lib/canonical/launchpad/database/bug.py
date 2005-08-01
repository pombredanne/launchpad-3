# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Launchpad bug-related database table classes."""

__metaclass__ = type
__all__ = ['Bug', 'BugFactory', 'BugSet']

from sets import Set
from email.Utils import make_msgid

from zope.interface import implements
from zope.exceptions import NotFoundError

from sqlobject import ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin
from sqlobject import SQLObjectNotFound

from canonical.launchpad.interfaces import IBug, IBugSet
from canonical.launchpad.helpers import contactEmailAddresses
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW, DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.lp import dbschema
from canonical.launchpad.database.bugset import BugSetBase
from canonical.launchpad.database.message import (
    Message, MessageChunk)
from canonical.launchpad.database.bugmessage import BugMessage
from canonical.launchpad.database.bugtask import BugTask
from canonical.launchpad.database.bugwatch import BugWatch
from canonical.launchpad.database.bugsubscription import BugSubscription
from canonical.launchpad.database.maintainership import Maintainership

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
    bugtasks = MultipleJoin('BugTask', joinColumn='bug', orderBy='id')
    productinfestations = MultipleJoin(
            'BugProductInfestation', joinColumn='bug', orderBy='id')
    packageinfestations = MultipleJoin(
            'BugPackageInfestation', joinColumn='bug', orderBy='id')
    watches = MultipleJoin('BugWatch', joinColumn='bug')
    externalrefs = MultipleJoin(
            'BugExternalRef', joinColumn='bug', orderBy='id')
    cverefs = MultipleJoin('CVERef', joinColumn='bug', orderBy='cveref')
    subscriptions = MultipleJoin(
            'BugSubscription', joinColumn='bug', orderBy='id')
    duplicates = MultipleJoin('Bug', joinColumn='duplicateof', orderBy='id')

    def followup_subject(self):
        return 'Re: '+ self.title

    def subscribe(self, person, subscription):
        """See canonical.launchpad.interfaces.IBug."""
        if self.isSubscribed(person):
            raise ValueError(
                _("Person with ID %d is already subscribed to this bug") %
                person.id)

        return BugSubscription(
            bug = self.id, person = person.id, subscription = subscription)

    def unsubscribe(self, person):
        """See canonical.launchpad.interfaces.IBug."""
        pass

    def isSubscribed(self, person):
        """See canonical.launchpad.interfaces.IBug."""
        bs = BugSubscription.selectBy(bugID = self.id, personID = person.id)
        return bool(bs.count())

    def notificationRecipientAddresses(self):
        """See canonical.launchpad.interfaces.IBug."""
        emails = Set()
        for subscription in self.subscriptions:
            if subscription.subscription == dbschema.BugSubscription.CC:
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

    def linkMessage(self, message):
        if message not in self.messages:
            BugMessage(bug=self, message=message)

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

    def addTask(self, owner, product=None, distribution=None,
        distrorelease=None, sourcepackagename=None,
        binarypackagename=None):
        """See IBug."""
        # look for a match among existing tasks
        for task in self.bugtasks:
            if (task.product == product and
                task.distribution == distribution and
                task.distrorelease == distrorelease and
                task.sourcepackagename == sourcepackagename and
                task.binarypackagename == binarypackagename):
                return task
        # create and return a new task
        return BugTask(owner=owner, product=product,
            distribution=distribution, distrorelease=distrorelease,
            sourcepackagename=sourcepackagename,
            binarypackagename=binarypackagename)


# XXX kiko 2005-07-15 should this go to BugSet.new?
def BugFactory(addview=None, distribution=None, sourcepackagename=None,
        binarypackagename=None, product=None, comment=None,
        description=None, msg=None, summary=None,
        datecreated=None, title=None, private=False, owner=None):
    """Create a bug and return it.

    Things to note when using this factory:

      * addview is not used for anything in this factory

      * if no description is passed, the comment will be used as the
        description

      * if summary is not passed then the summary will be the
        first sentence of the description

      * the submitter will be subscribed to the bug

      * if either product or distribution is specified, an appropiate
        bug task will be created

    """
    # make sure that the factory has been passed enough information
    if not (comment or description or msg is not None):
        raise ValueError(
            'BugFactory requires a comment, msg, or description')

    # make sure we did not get TOO MUCH information
    assert not (comment and msg is not None), "Too much information"

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

    sub = BugSubscription(
        person=owner.id, bug=bug.id, subscription=dbschema.BugSubscription.CC)

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
        return BugFactory(distribution=distribution,
            sourcepackagename=sourcepackagename,
            binarypackagename=binarypackagename, product=product,
            comment=comment, description=description, msg=msg,
            summary=summary, datecreated=datecreated, title=title,
            private=private, owner=owner)


