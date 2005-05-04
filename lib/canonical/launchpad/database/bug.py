# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Launchpad bug-related database table classes."""

__metaclass__ = type
__all__ = ['Bug', 'BugDelta', 'BugFactory', 'BugSet']

from sets import Set
from datetime import datetime
from email.Utils import make_msgid

from zope.interface import implements
from zope.exceptions import NotFoundError

from sqlobject import ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin

from canonical.launchpad.interfaces import \
    IBug, IBugAddForm, IBugSet, IBugDelta
from canonical.database.sqlbase import SQLBase
from canonical.database.constants import UTC_NOW, DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.lp import dbschema
from canonical.launchpad.database.bugset import BugSetBase
from canonical.launchpad.database.message \
        import Message, MessageSet, MessageChunk
from canonical.launchpad.database.bugmessage import BugMessage
from canonical.launchpad.database.bugtask import BugTask
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
    shortdesc = StringCol(notNull=False, default=None)
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
                           intermediateTable='BugMessage')
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

    def followup_title(self):
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
                preferred_email = subscription.person.preferredemail
                # XXX: Brad Bollenbach, 2005-03-14: Subscribed users
                # should always have a preferred email, but
                # realistically, we've got some corruption in our db
                # still that prevents us from guaranteeing that all
                # subscribers will have a preferredemail
                if preferred_email:
                    emails.add(preferred_email.email)

        if not self.private:
            # Collect implicit subscriptions. This only happens on
            # public bugs.
            for task in self.bugtasks:
                if task.assignee:
                    preferred_email = task.assignee.preferredemail
                    # XXX: Brad Bollenbach, 2005-03-14: Subscribed users
                    # should always have a preferred email, but
                    # realistically, we've got some corruption in our db
                    # still that prevents us from guaranteeing that all
                    # subscribers will have a preferredemail
                    if preferred_email:
                        emails.add(preferred_email.email)

                if task.product:
                    preferred_email = task.product.owner.preferredemail
                    if preferred_email:
                        emails.add(preferred_email.email)
                else:
                    if task.sourcepackagename:
                        if task.distribution:
                            distribution = task.distribution
                        else:
                            distribution = task.distrorelease.distribution
                        maintainership = Maintainership.selectOneBy(
                            sourcepackagenameID = task.sourcepackagename.id,
                            distributionID = distribution.id)
                        if maintainership is not None:
                            maintainer = maintainership.maintainer
                            preferred_email = maintainer.preferredemail
                            if preferred_email:
                                emails.add(preferred_email.email)

        preferred_email = self.owner.preferredemail
        if preferred_email:
            emails.add(preferred_email.email)
        emails = list(emails)
        emails.sort()
        return emails


class BugDelta:
    """See canonical.launchpad.interfaces.IBugDelta."""
    implements(IBugDelta)
    def __init__(self, bug, bugurl, user, title=None, shortdesc=None,
                 description=None, name=None, private=None,
                 external_reference=None, bugwatch=None, cveref=None,
                 bugtask_deltas=None):
        self.bug = bug
        self.bugurl = bugurl
        self.user = user
        self.title = title
        self.shortdesc = shortdesc
        self.description = description
        self.name = name
        self.private = private
        self.external_reference = external_reference
        self.bugwatch = bugwatch
        self.cveref = cveref
        self.bugtask_deltas = bugtask_deltas

def BugFactory(addview=None, distribution=None, sourcepackagename=None,
               binarypackagename=None, product=None, comment=None,
               description=None, rfc822msgid=None, shortdesc=None,
               datecreated=None, title=None, private=False,
               owner=None):
    """Create a bug.

    Things to note when using this factory:

      * addview is not used for anything in this factory

      * one of either distribution or product must be provided. If neither
        are provided, a ValueError will be raised

      * if no description is passed, the comment will be used as the
        description

      * if shortdesc is not passed then the shortdesc will be the
        first sentence of the description

      * the appropriate bug task (exactly one, from this function) and
        subscriptions will be added

      * the return value is an IBugAddForm to play nicely with the Z3
        addform machinery
    """

    # make sure that the factory has been passed enough information
    if not (distribution or product):
        raise ValueError('Must pass BugFactory a distribution or a product')
    if not (comment or description or rfc822msgid):
        raise ValueError(
            'BugFactory requires a comment, rfc822msgid or description')

    # extract the details needed to create the bug and optional msg
    if not description:
        description = comment

    # if we have been passed only a description, then we set the summary to
    # be the first paragraph of it, up to 320 characters long
    if description and not shortdesc:
        shortdesc = description.split('. ')[0]
        if len(shortdesc) > 320:
            shortdesc = shortdesc[:320] + '...'

    if not datecreated:
        datecreated = UTC_NOW

    bug = Bug(
        title=title, shortdesc=shortdesc,
        description=description, private=private,
        owner=owner.id, datecreated=datecreated)

    BugSubscription(
        person=owner.id, bug=bug.id, subscription=dbschema.BugSubscription.CC)

    # create the bug comment if one was given
    if comment:
        if not rfc822msgid:
            rfc822msgid = make_msgid('malonedeb')

    # retrieve or create the message in the db
    msg_set = MessageSet()
    try:
        msg = msg_set.get(rfc822msgid=rfc822msgid)
    except NotFoundError:
        msg = Message(
            title=title, distribution=distribution,
            rfc822msgid=rfc822msgid, owner=owner)
        chunk = MessageChunk(
                messageID=msg.id, sequence=1, content=comment, blobID=None)

    # link the bug to the message
    bugmsg = BugMessage(bugID=bug.id, messageID=msg.id)

    # create the task on a product if one was passed
    if product:
        BugTask(bug=bug, product=product.id, owner=owner.id)

    # create the task on a source package name if one was passed
    if distribution:
        BugTask(
            bug=bug,
            distribution=distribution,
            sourcepackagename=sourcepackagename,
            binarypackagename=binarypackagename,
            owner=owner.id)

    class BugAdded:
        implements(IBugAddForm)
        def __init__(self, **kw):
            for attr, val in kw.items():
                setattr(self, attr, val)

    bug_added = BugAdded(
        distribution=distribution, sourcepackagename=sourcepackagename,
        binarypackagename=binarypackagename, product=product,
        comment=comment, description=description, rfc822msgid=rfc822msgid,
        shortdesc=shortdesc, datecreated=datecreated, title=title,
        private=private, owner=owner)
    bug_added.id = bug.id

    return bug_added


class BugSet(BugSetBase):
    """A set for bugs."""

    implements(IBugSet)
    table = Bug

    def __getitem__(self, id):
        """See canonical.launchpad.interfaces.bug.IBugSet."""
        item = self.table.selectOne(self.table.q.id==id)
        if item is None:
            raise KeyError, id

    def __iter__(self):
        """See canonical.launchpad.interfaces.bug.IBugSet."""
        for row in self.table.select():
            yield row

    def get(self, bugid):
        """See canonical.launchpad.interfaces.bug.IBugSet."""
        return self.table.get(bugid)

