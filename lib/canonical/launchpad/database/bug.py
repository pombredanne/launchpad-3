"""Launchpad Bug-related Database Table Objects

Part of the Launchpad system.

(c) 2004 Canonical, Ltd.
"""

from sets import Set
from datetime import datetime
from email.Utils import make_msgid

from zope.interface import implements

from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.launchpad.interfaces import IBug, IBugAddForm, IBugSet
from canonical.database.sqlbase import SQLBase
from canonical.database.constants import nowUTC, DEFAULT
from canonical.lp import dbschema
from canonical.launchpad.database.bugset import BugSetBase
from canonical.launchpad.database.message import Message, MessageSet
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
    duplicateof = ForeignKey(dbName='duplicateof', foreignKey='Bug', default=None)
    datecreated = DateTimeCol(notNull=True, default=nowUTC)
    communityscore = IntCol(dbName='communityscore', notNull=True, default=0)
    communitytimestamp = DateTimeCol(dbName='communitytimestamp',
                                     notNull=True, default=DEFAULT)
    hits = IntCol(dbName='hits', notNull=True, default=0)
    hitstimestamp = DateTimeCol(dbName='hitstimestamp', notNull=True,
                                default=DEFAULT)
    activityscore = IntCol(dbName='activityscore', notNull=True, default=0)
    activitytimestamp = DateTimeCol(dbName='activitytimestamp', notNull=True,
                                    default=DEFAULT)
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
        bs = BugSubscription.selectBy(
            bugID = self.id, personID = person.id)
        if bs.count():
            return True
        else:
            return False

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
                        maintainership = Maintainership.selectBy(
                            sourcepackagenameID = task.sourcepackagename.id,
                            distributionID = distribution.id)
                        if maintainership.count():
                            preferred_email = maintainership[0].maintainer.preferredemail
                            if preferred_email:
                                emails.add(preferred_email.email)

        preferred_email = self.owner.preferredemail
        if preferred_email:
            emails.add(preferred_email.email)
        emails = list(emails)
        emails.sort()
        return emails


def BugFactory(*args, **kw):
    """Create a bug from an IBugAddForm. Note some unusual behaviour in this
    Factory:

      - the Summary and Description are not normally passed, we generally
        like to create bugs with just a title and a first comment, and let
        expert users create the summary and description if needed.
      - if a Description is passed without a Summary, then the summary will
        be the first sentence of the description.
      - it is an error to pass neither a product nor a package.
    """

    # make sure that the factory has been passed enough information
    if not (kw.get('distribution') or kw.get('product')):
        raise ValueError, 'Must pass BugFactory a distro or a product'
    if not (kw.get('comment', None) or
            kw.get('description', None) or
            kw.get('rfc822msgid', None)):
        raise ValueError, 'BugFactory requires a comment, rfc822msgid or description'
    # extract the details needed to create the bug and optional msg
    description = kw.get('description', None)
    summary = kw.get('shortdesc', None)
    # if we have been passed only a description, then we set the summary to
    # be the first paragraph of it, up to 320 characters long
    if description and not summary:
        summary = description.split('. ')[0]
        if len(summary) > 320:
            summary = summary[:320] + '...'
    datecreated = kw.get('datecreated', datetime.now())
    bug = Bug(
        title = kw['title'],
        shortdesc = summary,
        description = description,
        private = kw.get("private", False),
        owner = kw['owner'].id,
        datecreated=datecreated)

    if kw.get("private"):
        if kw.get("product"):
            # subscribe the upstream maintainer on a private bug, to
            # ensure they can actually see it!
            BugSubscription(
                person = kw['product'].owner.id, bug = bug.id,
                subscription = dbschema.BugSubscription.CC)
        elif kw.get("sourcepackagename"):
            spn = kw.get("sourcepackagename")
            distributionid = kw.get("distribution")
            if spn and distributionid:
                maintainerships = Maintainership.selectBy(
                    sourcepackagenameID=spn.id,
                    distributionID=distributionid)
                if maintainerships.count():
                    BugSubscription(
                        person = maintainerships[0].maintainer.id,
                        bug = bug.id,
                        subscription = dbschema.BugSubscription.CC)

    BugSubscription(
        person = kw['owner'].id, bug = bug.id,
        subscription = dbschema.BugSubscription.CC)

    # create the bug comment if one was given
    if kw.get('comment', None):
        if not kw.get('rfc822msgid', None):
            kw['rfc822msgid'] = make_msgid('malonedeb')
    # retrieve or create the message in the db
    try:
        msg = MessageSet().get(rfc822msgid=kw['rfc822msgid'])
    except IndexError:
        msg = Message(title=kw['title'],
            contents = kw['comment'],
            distribution = kw.get('distribution', None),
            rfc822msgid = kw['rfc822msgid'],
            owner = kw['owner'])

    # link the bug to the message
    bugmsg = BugMessage(bugID=bug.id, messageID=msg.id)

    # create the task on a product if one was passed
    if kw.get('product', None):
        BugTask(
            bug = bug,
            product = kw['product'].id,
            owner = kw['owner'].id)
    # create the task on a source package name if one was passed
    if kw.get('distribution', None):
        BugTask(
            bug = bug,
            distribution = kw['distribution'],
            sourcepackagename = kw['sourcepackagename'],
            binarypackagename = kw.get('binarypackagename', None),
            owner = kw['owner'].id)

    class BugAdded(object):
        implements(IBugAddForm)
        def __init__(self, **kw):
            for attr, val in kw.items():
                setattr(self, attr, val)

    bug_added = BugAdded(**kw)
    bug_added.id = bug.id

    return bug_added

class BugSet(BugSetBase):
    """A set for bugs."""

    implements(IBugSet)
    table = Bug

    def __getitem__(self, id):
        """See canonical.launchpad.interfaces.bug.IBugSet."""
        try:
            return self.table.select(self.table.q.id==id)[0]
        except IndexError:
            # Convert IndexError to KeyErrors to get Zope's NotFound page
            raise KeyError, id

    def __iter__(self):
        """See canonical.launchpad.interfaces.bug.IBugSet."""
        for row in self.table.select():
            yield row

    def get(self, bugid):
        """See canonical.launchpad.interfaces.bug.IBugSet."""
        return self.table.get(bugid)
