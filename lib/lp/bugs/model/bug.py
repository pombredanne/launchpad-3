# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

"""Launchpad bug-related database table classes."""

__metaclass__ = type

__all__ = [
    'Bug',
    'BugAffectsPerson',
    'BugBecameQuestionEvent',
    'BugMute',
    'BugSet',
    'BugTag',
    'FileBugData',
    'get_also_notified_subscribers',
    'get_bug_tags',
    'get_bug_tags_open_count',
    ]


from cStringIO import StringIO
from datetime import (
    datetime,
    timedelta,
    )
from email.Utils import make_msgid
from functools import wraps
from itertools import chain
import operator
import re

from lazr.lifecycle.event import (
    ObjectCreatedEvent,
    ObjectDeletedEvent,
    ObjectModifiedEvent,
    )
from lazr.lifecycle.snapshot import Snapshot
import pytz
from pytz import timezone
from sqlobject import (
    BoolCol,
    ForeignKey,
    IntCol,
    SQLMultipleJoin,
    SQLObjectNotFound,
    SQLRelatedJoin,
    StringCol,
    )
from storm.expr import (
    And,
    Desc,
    In,
    Join,
    LeftJoin,
    Max,
    Not,
    Or,
    Select,
    SQL,
    Sum,
    Union,
    )
from storm.info import ClassAlias
from storm.locals import (
    DateTime,
    Int,
    Reference,
    )
from storm.store import (
    EmptyResultSet,
    Store,
    )
from zope.component import getUtility
from zope.contenttype import guess_content_type
from zope.event import notify
from zope.interface import (
    implements,
    providedBy,
    )
from zope.security.proxy import (
    ProxyFactory,
    removeSecurityProxy,
    )

from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import (
    cursor,
    SQLBase,
    sqlvalues,
    )
from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from canonical.launchpad.database.librarian import (
    LibraryFileAlias,
    LibraryFileContent,
    )
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.interfaces.launchpad import IHasBug
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    ILaunchBag,
    IStoreSelector,
    MAIN_STORE,
    )
from lp.answers.interfaces.questiontarget import IQuestionTarget
from lp.app.enums import ServiceUsage
from lp.app.errors import (
    NotFoundError,
    UserCannotUnsubscribePerson,
    )
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.app.validators import LaunchpadValidationError
from lp.bugs.adapters.bugchange import (
    BranchLinkedToBug,
    BranchUnlinkedFromBug,
    BugConvertedToQuestion,
    BugDuplicateChange,
    BugWatchAdded,
    BugWatchRemoved,
    SeriesNominated,
    UnsubscribedFromBug,
    )
from lp.bugs.enum import BugNotificationLevel
from lp.bugs.errors import InvalidDuplicateValue
from lp.bugs.interfaces.bug import (
    IBug,
    IBugBecameQuestionEvent,
    IBugMute,
    IBugSet,
    IFileBugData,
    )
from lp.bugs.interfaces.bugactivity import IBugActivitySet
from lp.bugs.interfaces.bugattachment import (
    BugAttachmentType,
    IBugAttachmentSet,
    )
from lp.bugs.interfaces.bugmessage import IBugMessageSet
from lp.bugs.interfaces.bugnomination import (
    NominationError,
    NominationSeriesObsoleteError,
    )
from lp.bugs.interfaces.bugnotification import IBugNotificationSet
from lp.bugs.interfaces.bugtask import (
    BugTaskStatus,
    BugTaskStatusSearch,
    IBugTask,
    IBugTaskSet,
    UNRESOLVED_BUGTASK_STATUSES,
    )
from lp.bugs.interfaces.bugtracker import BugTrackerType
from lp.bugs.interfaces.bugwatch import IBugWatchSet
from lp.bugs.interfaces.cve import ICveSet
from lp.bugs.mail.bugnotificationrecipients import BugNotificationRecipients
from lp.bugs.model.bugactivity import BugActivity
from lp.bugs.model.bugattachment import BugAttachment
from lp.bugs.model.bugbranch import BugBranch
from lp.bugs.model.bugcve import BugCve
from lp.bugs.model.bugmessage import BugMessage
from lp.bugs.model.bugnomination import BugNomination
from lp.bugs.model.bugnotification import BugNotification
from lp.bugs.model.bugsubscription import BugSubscription
from lp.bugs.model.bugtarget import OfficialBugTag
from lp.bugs.model.bugtask import (
    BugTask,
    bugtask_sort_key,
    get_bug_privacy_filter,
    )
from lp.bugs.model.bugwatch import BugWatch
from lp.bugs.model.structuralsubscription import (
    get_structural_subscriptions_for_bug,
    get_structural_subscribers,
    )
from lp.code.interfaces.branchcollection import IAllBranches
from lp.hardwaredb.interfaces.hwdb import IHWSubmissionBugSet
from lp.registry.interfaces.accesspolicy import UnsuitableAccessPolicyError
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.person import (
    IPersonSet,
    validate_person,
    validate_public_person,
    )
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.role import IPersonRoles
from lp.registry.interfaces.series import SeriesStatus
from lp.registry.interfaces.sourcepackage import ISourcePackage
from lp.registry.model.person import (
    Person,
    person_sort_key,
    PersonSet,
    )
from lp.registry.model.pillar import pillar_sort_key
from lp.registry.model.teammembership import TeamParticipation
from lp.services.database.stormbase import StormBase
from lp.services.features import getFeatureFlag
from lp.services.fields import DuplicateBug
from lp.services.messages.interfaces.message import (
    IMessage,
    IndexedMessage,
    )
from lp.services.messages.model.message import (
    Message,
    MessageChunk,
    MessageSet,
    )
from lp.services.propertycache import (
    cachedproperty,
    clear_property_cache,
    get_property_cache,
    )


_bug_tag_query_template = """
        SELECT %(columns)s FROM %(tables)s WHERE
            %(condition)s GROUP BY BugTag.tag ORDER BY BugTag.tag"""


def snapshot_bug_params(bug_params):
    """Return a snapshot of a `CreateBugParams` object."""
    return Snapshot(
        bug_params, names=[
            "owner", "title", "comment", "description", "msg",
            "datecreated", "security_related", "private",
            "distribution", "sourcepackagename",
            "product", "status", "subscribers", "tags",
            "subscribe_owner", "filed_by", "importance",
            "milestone", "assignee", "cve"])


class BugTag(SQLBase):
    """A tag belonging to a bug."""

    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    tag = StringCol(notNull=True)


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


def get_bug_tags_open_count(context_condition, user, tag_limit=0,
    include_tags=None):
    """Worker for IBugTarget.getUsedBugTagsWithOpenCounts.

    See `IBugTarget` for details.

    The only change is that this function takes a SQL expression for limiting
    the found tags.
    :param context_condition: A Storm SQL expression, limiting the
        used tags to a specific context. Only the BugSummary table may be
        used to choose the context. If False then no query will be performed
        (and {} returned).
    """
    # Circular fail.
    from lp.bugs.model.bugsummary import BugSummary
    tags = {}
    if include_tags:
        tags = dict((tag, 0) for tag in include_tags)
    store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
    admin_team = getUtility(ILaunchpadCelebrities).admin
    if user is not None and not user.inTeam(admin_team):
        store = store.with_(SQL(
            "teams AS ("
            "SELECT team from TeamParticipation WHERE person=?)", (user.id,)))
    where_conditions = [
        BugSummary.status.is_in(UNRESOLVED_BUGTASK_STATUSES),
        BugSummary.tag != None,
        context_condition,
        ]
    if user is None:
        where_conditions.append(BugSummary.viewed_by_id == None)
    elif not user.inTeam(admin_team):
        where_conditions.append(
            Or(
                BugSummary.viewed_by_id == None,
                BugSummary.viewed_by_id.is_in(SQL("SELECT team FROM teams"))
                ))
    sum_count = Sum(BugSummary.count)
    tag_count_columns = (BugSummary.tag, sum_count)

    # Always query for used
    def _query(*args):
        return store.find(tag_count_columns, *(where_conditions + list(args))
            ).group_by(BugSummary.tag).having(sum_count != 0).order_by(
            Desc(Sum(BugSummary.count)), BugSummary.tag)
    used = _query()
    if tag_limit:
        used = used[:tag_limit]
    if include_tags:
        # Union in a query for just include_tags.
        used = used.union(_query(BugSummary.tag.is_in(include_tags)))
    tags.update(dict(used))
    return tags


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
        storm_validator=validate_public_person, notNull=True)
    duplicateof = ForeignKey(
        dbName='duplicateof', foreignKey='Bug', default=None)
    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    date_last_updated = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    private = BoolCol(notNull=True, default=False)
    date_made_private = UtcDateTimeCol(notNull=False, default=None)
    who_made_private = ForeignKey(
        dbName='who_made_private', foreignKey='Person',
        storm_validator=validate_public_person, default=None)
    security_related = BoolCol(notNull=True, default=False)
    access_policy_id = Int(name="access_policy")
    access_policy = Reference(access_policy_id, 'AccessPolicy.id')

    # useful Joins
    activity = SQLMultipleJoin('BugActivity', joinColumn='bug', orderBy='id')
    messages = SQLRelatedJoin('Message', joinColumn='bug',
                           otherColumn='message',
                           intermediateTable='BugMessage',
                           prejoins=['owner'],
                           orderBy=['datecreated', 'id'])
    bug_messages = SQLMultipleJoin(
        'BugMessage', joinColumn='bug', orderBy='index')
    watches = SQLMultipleJoin(
        'BugWatch', joinColumn='bug', orderBy=['bugtracker', 'remotebug'])
    cves = SQLRelatedJoin('Cve', intermediateTable='BugCve',
        orderBy='sequence', joinColumn='bug', otherColumn='cve')
    cve_links = SQLMultipleJoin('BugCve', joinColumn='bug', orderBy='id')
    duplicates = SQLMultipleJoin(
        'Bug', joinColumn='duplicateof', orderBy='id')
    specifications = SQLRelatedJoin('Specification', joinColumn='bug',
        otherColumn='specification', intermediateTable='SpecificationBug',
        orderBy='-datecreated')
    questions = SQLRelatedJoin('Question', joinColumn='bug',
        otherColumn='question', intermediateTable='QuestionBug',
        orderBy='-datecreated')
    linked_branches = SQLMultipleJoin(
        'BugBranch', joinColumn='bug', orderBy='id')
    date_last_message = UtcDateTimeCol(default=None)
    number_of_duplicates = IntCol(notNull=True, default=0)
    message_count = IntCol(notNull=True, default=0)
    users_affected_count = IntCol(notNull=True, default=0)
    users_unaffected_count = IntCol(notNull=True, default=0)
    heat = IntCol(notNull=True, default=0)
    heat_last_updated = UtcDateTimeCol(default=None)
    latest_patch_uploaded = UtcDateTimeCol(default=None)

    @cachedproperty
    def _subscriber_cache(self):
        """Caches known subscribers."""
        return set()

    @cachedproperty
    def _subscriber_dups_cache(self):
        """Caches known subscribers to dupes."""
        return set()

    @cachedproperty
    def _unsubscribed_cache(self):
        """Cache known non-subscribers."""
        return set()

    @property
    def latest_patch(self):
        """See `IBug`."""
        # We want to retrieve the most recently added bug attachment
        # that is of type BugAttachmentType.PATCH. In order to find
        # this attachment, we should in theory sort by
        # BugAttachment.message.datecreated. Since we don't have
        # an index for Message.datecreated, such a query would be
        # quite slow. We search instead for the BugAttachment with
        # the largest ID for a given bug. This is "nearly" equivalent
        # to searching the record with the maximum value of
        # message.datecreated: The only exception is the rare case when
        # two BugAttachment records are simultaneuosly added to the same
        # bug, where bug_attachment_1.id < bug_attachment_2.id, while
        # the Message record for bug_attachment_2 is created before
        # the Message record for bug_attachment_1. The difference of
        # the datecreated values of the Message records is in this case
        # probably smaller than one second and the selection of the
        # "most recent" patch anyway somewhat arbitrary.
        return Store.of(self).find(
            BugAttachment, BugAttachment.id == Select(
                Max(BugAttachment.id),
                And(BugAttachment.bug == self.id,
                    BugAttachment.type == BugAttachmentType.PATCH))).one()

    @property
    def comment_count(self):
        """See `IBug`."""
        return self.message_count - 1

    @property
    def users_affected(self):
        """See `IBug`."""
        return Store.of(self).find(
            Person, BugAffectsPerson.person == Person.id,
            BugAffectsPerson.affected,
            BugAffectsPerson.bug == self)

    @property
    def users_unaffected(self):
        """See `IBug`."""
        return Store.of(self).find(
            Person, BugAffectsPerson.person == Person.id,
            Not(BugAffectsPerson.affected),
            BugAffectsPerson.bug == self)

    @property
    def user_ids_affected_with_dupes(self):
        """Return all IDs of Persons affected by this bug and its dupes.
        The return value is a Storm expression.  Running a query with
        this expression returns a result that may contain the same ID
        multiple times, for example if that person is affected via
        more than one duplicate."""
        return Union(
            Select(Person.id,
                   And(BugAffectsPerson.person == Person.id,
                       BugAffectsPerson.affected,
                       BugAffectsPerson.bug == self)),
            Select(Person.id,
                   And(BugAffectsPerson.person == Person.id,
                       BugAffectsPerson.bug == Bug.id,
                       BugAffectsPerson.affected,
                       Bug.duplicateof == self.id)))

    @property
    def users_affected_with_dupes(self):
        """See `IBug`."""
        return Store.of(self).find(
            Person,
            Person.id.is_in(self.user_ids_affected_with_dupes))

    @property
    def users_affected_count_with_dupes(self):
        """See `IBug`."""
        return self.users_affected_with_dupes.count()

    @property
    def indexed_messages(self):
        """See `IMessageTarget`."""
        # Note that this is a decorated result set, so will cache its
        # value (in the absence of slices)
        return self._indexed_messages(include_content=True)

    def _indexed_messages(self, include_content=False, include_parents=True):
        """Get the bugs messages, indexed.

        :param include_content: If True retrieve the content for the messages
            too.
        :param include_parents: If True retrieve the object for parent
            messages too. If False the parent attribute will be *forced* to
            None to reduce database lookups.
        """
        # Make all messages be 'in' the main bugtask.
        inside = self.default_bugtask
        store = Store.of(self)
        message_by_id = {}
        to_messages = lambda rows: [row[0] for row in rows]

        def eager_load_owners(messages):
            # Because we may have multiple owners, we spend less time
            # in storm with very large bugs by not joining and instead
            # querying a second time. If this starts to show high db
            # time, we can left outer join instead.
            owner_ids = set(message.ownerID for message in messages)
            owner_ids.discard(None)
            if not owner_ids:
                return
            list(store.find(Person, Person.id.is_in(owner_ids)))

        def eager_load_content(messages):
            # To avoid the complexity of having multiple rows per
            # message, or joining in the database (though perhaps in
            # future we should do that), we do a single separate query
            # for the message content.
            message_ids = set(message.id for message in messages)
            chunks = store.find(
                MessageChunk, MessageChunk.messageID.is_in(message_ids))
            chunks.order_by(MessageChunk.id)
            chunk_map = {}
            for chunk in chunks:
                message_chunks = chunk_map.setdefault(chunk.messageID, [])
                message_chunks.append(chunk)
            for message in messages:
                if message.id not in chunk_map:
                    continue
                cache = get_property_cache(message)
                cache.text_contents = Message.chunks_text(
                    chunk_map[message.id])

        def eager_load(rows):
            messages = to_messages(rows)
            eager_load_owners(messages)
            if include_content:
                eager_load_content(messages)

        def index_message(row):
            # convert row to an IndexedMessage
            if include_parents:
                message, parent, bugmessage = row
                if parent is not None:
                    # If there is an IndexedMessage available as parent, use
                    # that to reduce on-demand parent lookups.
                    parent = message_by_id.get(parent.id, parent)
            else:
                message, bugmessage = row
                parent = None  # parent attribute is not going to be accessed.
            index = bugmessage.index
            result = IndexedMessage(message, inside, index, parent)
            if include_parents:
                # This message may be the parent for another: stash it to
                # permit use.
                message_by_id[message.id] = result
            return result
        if include_parents:
            ParentMessage = ClassAlias(Message)
            ParentBugMessage = ClassAlias(BugMessage)
            tables = [
                Message,
                Join(
                    BugMessage,
                    BugMessage.messageID == Message.id),
                LeftJoin(
                    Join(
                        ParentMessage,
                        ParentBugMessage,
                        ParentMessage.id == ParentBugMessage.messageID),
                    And(
                        Message.parent == ParentMessage.id,
                        ParentBugMessage.bugID == self.id)),
                ]
            results = store.using(*tables).find(
                (Message, ParentMessage, BugMessage),
                BugMessage.bugID == self.id,
                )
        else:
            lookup = Message, BugMessage
            results = store.find(lookup,
                BugMessage.bugID == self.id,
                BugMessage.messageID == Message.id,
                )
        results.order_by(BugMessage.index)
        return DecoratedResultSet(results, index_message,
            pre_iter_hook=eager_load)

    @property
    def displayname(self):
        """See `IBug`."""
        dn = 'Bug #%d' % self.id
        if self.name:
            dn += ' (' + self.name + ')'
        return dn

    @cachedproperty
    def bugtasks(self):
        """See `IBug`."""
        # \o/ circular imports.
        from lp.registry.model.distribution import Distribution
        from lp.registry.model.distroseries import DistroSeries
        from lp.registry.model.product import Product
        from lp.registry.model.productseries import ProductSeries
        from lp.registry.model.sourcepackagename import SourcePackageName
        store = Store.of(self)
        tasks = list(store.find(BugTask, BugTask.bugID == self.id))
        # The bugtasks attribute is iterated in the API and web
        # services, so it needs to preload all related data otherwise
        # late evaluation is triggered in both places. Separately,
        # bugtask_sort_key requires the related products, series,
        # distros, distroseries and source package names to be loaded.
        ids = set(map(operator.attrgetter('assigneeID'), tasks))
        ids.update(map(operator.attrgetter('ownerID'), tasks))
        ids.discard(None)
        if ids:
            list(getUtility(IPersonSet).getPrecachedPersonsFromIDs(
                ids, need_validity=True))

        def load_something(attrname, klass):
            ids = set(map(operator.attrgetter(attrname), tasks))
            ids.discard(None)
            if not ids:
                return
            list(store.find(klass, klass.id.is_in(ids)))
        load_something('productID', Product)
        load_something('productseriesID', ProductSeries)
        load_something('distributionID', Distribution)
        load_something('distroseriesID', DistroSeries)
        load_something('sourcepackagenameID', SourcePackageName)
        list(store.find(BugWatch, BugWatch.bugID == self.id))
        return sorted(tasks, key=bugtask_sort_key)

    @property
    def default_bugtask(self):
        """See `IBug`."""
        return Store.of(self).find(
            BugTask, bug=self).order_by(BugTask.id).first()

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

        1. The bug is inactive; the last update of the bug is older than
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

        days_old = config.malone.days_before_expiration
        # Do the search as the Janitor, to ensure that this bug can be
        # found, even if it's private. We don't have access to the user
        # calling this property. If the user has access to view this
        # property, he has permission to see the bug, so we're not
        # exposing something we shouldn't. The Janitor has access to
        # view all bugs.
        bugtasks = getUtility(IBugTaskSet).findExpirableBugTasks(
            days_old, getUtility(ILaunchpadCelebrities).janitor, bug=self)
        return bugtasks.count() > 0

    def isExpirable(self, days_old=None):
        """See `IBug`."""

        # If days_old is None read it from the Launchpad configuration
        # and use that value
        if days_old is None:
            days_old = config.malone.days_before_expiration

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
            days_old, getUtility(ILaunchpadCelebrities).janitor, bug=self)
        return bugtasks.count() > 0

    @cachedproperty
    def initial_message(self):
        """See `IBug`."""
        store = Store.of(self)
        messages = store.find(
            Message,
            BugMessage.bug == self,
            BugMessage.message == Message.id).order_by('id')
        return messages.first()

    @cachedproperty
    def official_tags(self):
        """See `IBug`."""
        # Da circle of imports forces the locals.
        from lp.registry.model.distribution import Distribution
        from lp.registry.model.product import Product
        table = OfficialBugTag
        table = LeftJoin(
            table,
            Distribution,
            OfficialBugTag.distribution_id == Distribution.id)
        table = LeftJoin(
            table,
            Product,
            OfficialBugTag.product_id == Product.id)
        # When this method is typically called it already has the necessary
        # info in memory, so rather than rejoin with Product etc, we do this
        # bit in Python. If reviewing performance here feel free to change.
        clauses = []
        for task in self.bugtasks:
            clauses.append(
                # Storm cannot compile proxied objects.
                removeSecurityProxy(task.target._getOfficialTagClause()))
        clause = Or(*clauses)
        return list(Store.of(self).using(table).find(OfficialBugTag.tag,
            clause).order_by(OfficialBugTag.tag).config(distinct=True))

    def followup_subject(self):
        """See `IBug`."""
        return 'Re: ' + self.title

    @property
    def has_patches(self):
        """See `IBug`."""
        return self.latest_patch_uploaded is not None

    def subscribe(self, person, subscribed_by, suppress_notify=True,
                  level=None):
        """See `IBug`."""

        # first look for an existing subscription
        for sub in self.subscriptions:
            if sub.person.id == person.id:
                if level is not None:
                    sub.bug_notification_level = level
                    # Should subscribed_by be changed in this case?  Until
                    # proven otherwise, we will answer with "no."
                return sub

        if level is None:
            level = BugNotificationLevel.COMMENTS

        sub = BugSubscription(
            bug=self, person=person, subscribed_by=subscribed_by,
            bug_notification_level=level)

        # Ensure that the subscription has been flushed.
        Store.of(sub).flush()

        # In some cases, a subscription should be created without
        # email notifications.  suppress_notify determines if
        # notifications are sent.
        if suppress_notify is False:
            notify(ObjectCreatedEvent(sub, user=subscribed_by))

        self.updateHeat()
        return sub

    def unsubscribe(self, person, unsubscribed_by, **kwargs):
        """See `IBug`."""
        # Drop cached subscription info.
        clear_property_cache(self)
        # Ensure the unsubscriber is in the _known_viewer cache for the bug so
        # that the permissions are such that the operation can succeed.
        get_property_cache(self)._known_viewers = set([unsubscribed_by.id])
        if person is None:
            person = unsubscribed_by

        ignore_permissions = kwargs.get('ignore_permissions', False)
        recipients = kwargs.get('recipients')
        for sub in self.subscriptions:
            if sub.person.id == person.id:
                if (not ignore_permissions
                        and not sub.canBeUnsubscribedByUser(unsubscribed_by)):
                    raise UserCannotUnsubscribePerson(
                        '%s does not have permission to unsubscribe %s.' % (
                            unsubscribed_by.displayname,
                            person.displayname))

                self.addChange(UnsubscribedFromBug(
                        when=UTC_NOW, person=unsubscribed_by,
                        unsubscribed_user=person, **kwargs),
                    recipients=recipients)
                store = Store.of(sub)
                store.remove(sub)
                # Make sure that the subscription removal has been
                # flushed so that code running with implicit flushes
                # disabled see the change.
                store.flush()
                self.updateHeat()
                del get_property_cache(self)._known_viewers
                return

    def unsubscribeFromDupes(self, person, unsubscribed_by):
        """See `IBug`."""
        if person is None:
            person = unsubscribed_by

        bugs_unsubscribed = []
        for dupe in self.duplicates:
            if dupe.isSubscribed(person):
                dupe.unsubscribe(person, unsubscribed_by)
                bugs_unsubscribed.append(dupe)

        return bugs_unsubscribed

    def isSubscribed(self, person):
        """See `IBug`."""
        return self.personIsDirectSubscriber(person)

    def isSubscribedToDupes(self, person):
        """See `IBug`."""
        return self.personIsSubscribedToDuplicate(person)

    def _getMutes(self, person):
        store = Store.of(self)
        mutes = store.find(
            BugMute,
            BugMute.bug == self,
            BugMute.person == person)
        return mutes

    def isMuted(self, person):
        """See `IBug`."""
        mutes = self._getMutes(person)
        return not mutes.is_empty()

    def mute(self, person, muted_by):
        """See `IBug`."""
        if person is None:
            # This may be a webservice request.
            person = muted_by
        assert not person.is_team, (
            "Muting a subscription for entire team is not allowed.")

        # If it's already muted, ignore the request.
        mutes = self._getMutes(person)
        if mutes.is_empty():
            mute = BugMute(person, self)
            Store.of(mute).flush()
        else:
            # It's already muted, pass.
            pass

    def unmute(self, person, unmuted_by):
        """See `IBug`."""
        store = Store.of(self)
        if person is None:
            # This may be a webservice request.
            person = unmuted_by
        mutes = self._getMutes(person)
        store.remove(mutes.one())
        return self.getSubscriptionForPerson(person)

    @property
    def subscriptions(self):
        """The set of `BugSubscriptions` for this bug."""
        # XXX: kiko 2006-09-23: Why is subscriptions ordered by ID?
        results = Store.of(self).find(
            (Person, BugSubscription),
            BugSubscription.person_id == Person.id,
            BugSubscription.bug_id == self.id).order_by(BugSubscription.id)
        return DecoratedResultSet(results, operator.itemgetter(1))

    def getSubscriptionInfo(self, level=BugNotificationLevel.LIFECYCLE):
        """See `IBug`."""
        return BugSubscriptionInfo(self, level)

    def getDirectSubscriptions(self):
        """See `IBug`."""
        return self.getSubscriptionInfo().direct_subscriptions

    def getDirectSubscribers(self, recipients=None, level=None):
        """See `IBug`.

        The recipients argument is private and not exposed in the
        interface. If a BugNotificationRecipients instance is supplied,
        the relevant subscribers and rationales will be registered on
        it.
        """
        if level is None:
            level = BugNotificationLevel.LIFECYCLE
        direct_subscribers = (
            self.getSubscriptionInfo(level).direct_subscribers)
        if recipients is not None:
            for subscriber in direct_subscribers:
                recipients.addDirectSubscriber(subscriber)
        return direct_subscribers.sorted

    def getDirectSubscribersWithDetails(self):
        """See `IBug`."""
        SubscribedBy = ClassAlias(Person, name="subscribed_by")
        results = Store.of(self).find(
            (Person, SubscribedBy, BugSubscription),
            BugSubscription.person_id == Person.id,
            BugSubscription.bug_id == self.id,
            BugSubscription.subscribed_by_id == SubscribedBy.id,
            Not(In(BugSubscription.person_id,
                   Select(BugMute.person_id, BugMute.bug_id == self.id)))
            ).order_by(Person.displayname)
        return results

    def getIndirectSubscribers(self, recipients=None, level=None):
        """See `IBug`.

        See the comment in getDirectSubscribers for a description of the
        recipients argument.
        """
        # "Also notified" and duplicate subscribers are mutually
        # exclusive, so return both lists.
        indirect_subscribers = chain(
            self.getAlsoNotifiedSubscribers(recipients, level),
            self.getSubscribersFromDuplicates(recipients, level))

        # Remove security proxy for the sort key, but return
        # the regular proxied object.
        return sorted(
            indirect_subscribers,
            key=lambda x: removeSecurityProxy(x).displayname)

    def getSubscriptionsFromDuplicates(self, recipients=None):
        """See `IBug`."""
        if self.private:
            return []
        # For each subscription to each duplicate of this bug, find the
        # earliest subscription for each subscriber. Eager load the
        # subscribers.
        return DecoratedResultSet(
            IStore(BugSubscription).find(
                (Person, BugSubscription),
                Bug.duplicateof == self,
                BugSubscription.bug_id == Bug.id,
                BugSubscription.person_id == Person.id).order_by(
                BugSubscription.person_id).config(
                    distinct=(BugSubscription.person_id,)),
            operator.itemgetter(1))

    def getSubscribersFromDuplicates(self, recipients=None, level=None):
        """See `IBug`.

        See the comment in getDirectSubscribers for a description of the
        recipients argument.
        """
        if level is None:
            level = BugNotificationLevel.LIFECYCLE
        info = self.getSubscriptionInfo(level)

        if recipients is not None:
            # Pre-load duplicate bugs.
            list(self.duplicates)
            for subscription in info.duplicate_only_subscriptions:
                recipients.addDupeSubscriber(
                    subscription.person, subscription.bug)
        return info.duplicate_only_subscriptions.subscribers.sorted

    def getSubscribersForPerson(self, person):
        """See `IBug."""

        assert person is not None

        def cache_unsubscribed(rows):
            if not rows:
                self._unsubscribed_cache.add(person)

        def cache_subscriber(row):
            subscriber, subscription = row
            if subscription.bug_id == self.id:
                self._subscriber_cache.add(subscriber)
            else:
                self._subscriber_dups_cache.add(subscriber)
            return subscriber
        return DecoratedResultSet(Store.of(self).find(
             # Return people and subscriptions
            (Person, BugSubscription),
            # For this bug or its duplicates
            Or(
                Bug.id == self.id,
                Bug.duplicateof == self.id),
            # Get subscriptions for these bugs
            BugSubscription.bug_id == Bug.id,
            # Filter by subscriptions to any team person is in.
            # Note that teamparticipation includes self-participation entries
            # (person X is in the team X)
            TeamParticipation.person == person.id,
            # XXX: Storm fails to compile this, so manually done.
            # bug=https://bugs.launchpad.net/storm/+bug/627137
            # RBC 20100831
            SQL("""TeamParticipation.team = BugSubscription.person"""),
            # Join in the Person rows we want
            # XXX: Storm fails to compile this, so manually done.
            # bug=https://bugs.launchpad.net/storm/+bug/627137
            # RBC 20100831
            SQL("""Person.id = TeamParticipation.team"""),
            ).order_by(Person.name).config(
                distinct=(Person.name, BugSubscription.person_id)),
            cache_subscriber, pre_iter_hook=cache_unsubscribed)

    def getSubscriptionForPerson(self, person):
        """See `IBug`."""
        store = Store.of(self)
        return store.find(
            BugSubscription,
            BugSubscription.person == person,
            BugSubscription.bug == self).one()

    def getAlsoNotifiedSubscribers(self, recipients=None, level=None):
        """See `IBug`.

        See the comment in getDirectSubscribers for a description of the
        recipients argument.
        """
        return get_also_notified_subscribers(self, recipients, level)

    def getBugNotificationRecipients(self, duplicateof=None, old_bug=None,
                                     level=None,
                                     include_master_dupe_subscribers=False):
        """See `IBug`."""
        recipients = BugNotificationRecipients(duplicateof=duplicateof)
        self.getDirectSubscribers(recipients, level=level)
        if self.private:
            assert self.getIndirectSubscribers() == [], (
                "Indirect subscribers found on private bug. "
                "A private bug should never have implicit subscribers!")
        else:
            self.getIndirectSubscribers(recipients, level=level)
            if include_master_dupe_subscribers and self.duplicateof:
                # This bug is a public duplicate of another bug, so include
                # the dupe target's subscribers in the recipient list. Note
                # that we only do this for duplicate bugs that are public;
                # changes in private bugs are not broadcast to their dupe
                # targets.
                dupe_recipients = (
                    self.duplicateof.getBugNotificationRecipients(
                        duplicateof=self.duplicateof, level=level))
                recipients.update(dupe_recipients)
        # XXX Tom Berger 2008-03-18:
        # We want to look up the recipients for `old_bug` too,
        # but for this to work, this code has to move out of the
        # class and into a free function, since `old_bug` is a
        # `Snapshot`, and doesn't have any of the methods of the
        # original `Bug`.
        return recipients

    def addCommentNotification(self, message, recipients=None, activity=None):
        """See `IBug`."""
        if recipients is None:
            recipients = self.getBugNotificationRecipients(
                level=BugNotificationLevel.COMMENTS)
        getUtility(IBugNotificationSet).addNotification(
             bug=self, is_comment=True,
             message=message, recipients=recipients, activity=activity)

    def addChange(self, change, recipients=None, deferred=False):
        """See `IBug`."""
        when = change.when
        if when is None:
            when = UTC_NOW

        activity_data = change.getBugActivity()
        if activity_data is not None:
            activity = getUtility(IBugActivitySet).new(
                self, when, change.person,
                activity_data['whatchanged'],
                activity_data.get('oldvalue'),
                activity_data.get('newvalue'),
                activity_data.get('message'))
        else:
            activity = None

        notification_data = change.getBugNotification()
        if notification_data is not None:
            assert notification_data.get('text') is not None, (
                "notification_data must include a `text` value.")
            message = MessageSet().fromText(
                self.followup_subject(), notification_data['text'],
                owner=change.person, datecreated=when)
            if recipients is None:
                recipients = self.getBugNotificationRecipients(
                    level=BugNotificationLevel.METADATA)
            getUtility(IBugNotificationSet).addNotification(
                bug=self, is_comment=False, message=message,
                recipients=recipients, activity=activity,
                deferred=deferred)

        self.updateHeat()

    def expireNotifications(self):
        """See `IBug`."""
        for notification in BugNotification.selectBy(
                bug=self, date_emailed=None):
            notification.date_emailed = UTC_NOW
            notification.syncUpdate()

    def newMessage(self, owner=None, subject=None,
                   content=None, parent=None, bugwatch=None,
                   remote_comment_id=None):
        """Create a new Message and link it to this bug."""
        if subject is None:
            subject = self.followup_subject()
        msg = Message(
            parent=parent, owner=owner, subject=subject,
            rfc822msgid=make_msgid('malone'))
        MessageChunk(message=msg, content=content, sequence=1)

        bugmsg = self.linkMessage(
            msg, bugwatch, remote_comment_id=remote_comment_id)
        if not bugmsg:
            return

        notify(ObjectCreatedEvent(bugmsg, user=owner))

        return bugmsg.message

    def linkMessage(self, message, bugwatch=None, user=None,
                    remote_comment_id=None):
        """See `IBug`."""
        if message not in self.messages:
            if user is None:
                user = message.owner
            result = BugMessage(bug=self, message=message,
                bugwatch=bugwatch, remote_comment_id=remote_comment_id,
                index=self.bug_messages.count())
            getUtility(IBugWatchSet).fromText(
                message.text_contents, self, user)
            self.findCvesInText(message.text_contents, user)
            for bugtask in self.bugtasks:
                # Check the stored value so we don't write to unaltered tasks.
                if (bugtask._status in (
                    BugTaskStatus.INCOMPLETE,
                    BugTaskStatusSearch.INCOMPLETE_WITHOUT_RESPONSE)):
                    # This is not a semantic change, so we don't update date
                    # records or send email.
                    bugtask._status = (
                        BugTaskStatusSearch.INCOMPLETE_WITH_RESPONSE)
            # XXX 2008-05-27 jamesh:
            # Ensure that BugMessages get flushed in same order as
            # they are created.
            Store.of(result).flush()
            return result

    def addTask(self, owner, target):
        """See `IBug`."""
        new_task = getUtility(IBugTaskSet).createTask(self, owner, target)

        # When a new task is added the bug's heat becomes relevant to the
        # target's max_bug_heat.
        target.recalculateBugHeatCache()

        return new_task

    def addWatch(self, bugtracker, remotebug, owner):
        """See `IBug`."""
        # We shouldn't add duplicate bug watches.
        bug_watch = self.getBugWatch(bugtracker, remotebug)
        if bug_watch is None:
            bug_watch = BugWatch(
                bug=self, bugtracker=bugtracker,
                remotebug=remotebug, owner=owner)
            Store.of(bug_watch).flush()
        self.addChange(BugWatchAdded(UTC_NOW, owner, bug_watch))
        notify(ObjectCreatedEvent(bug_watch, user=owner))
        return bug_watch

    def removeWatch(self, bug_watch, user):
        """See `IBug`."""
        self.addChange(BugWatchRemoved(UTC_NOW, user, bug_watch))
        bug_watch.destroySelf()

    def addAttachment(self, owner, data, comment, filename, is_patch=False,
                      content_type=None, description=None):
        """See `IBug`."""
        if isinstance(data, str):
            filecontent = data
        else:
            filecontent = data.read()

        if is_patch:
            content_type = 'text/plain'
        else:
            if content_type is None:
                content_type, encoding = guess_content_type(
                    name=filename, body=filecontent)

        filealias = getUtility(ILibraryFileAliasSet).create(
            name=filename, size=len(filecontent),
            file=StringIO(filecontent), contentType=content_type,
            restricted=self.private)

        return self.linkAttachment(
            owner, filealias, comment, is_patch, description)

    def linkAttachment(self, owner, file_alias, comment, is_patch=False,
                       description=None, send_notifications=True):
        """See `IBug`.

        This method should only be called by addAttachment() and
        FileBugViewBase.submit_bug_action, otherwise
        we may get inconsistent settings of bug.private and
        file_alias.restricted.

        :param send_notifications: Control sending of notifications for this
            attachment. This is disabled when adding attachments from 'extra
            data' in the filebug form, because that triggered hundreds of DB
            inserts and thus timeouts. Defaults to sending notifications.
        """
        if is_patch:
            attach_type = BugAttachmentType.PATCH
        else:
            attach_type = BugAttachmentType.UNSPECIFIED

        if description:
            title = description
        else:
            title = file_alias.filename

        if IMessage.providedBy(comment):
            message = comment
        else:
            message = self.newMessage(
                owner=owner, subject=description, content=comment)

        return getUtility(IBugAttachmentSet).create(
            bug=self, filealias=file_alias, attach_type=attach_type,
            title=title, message=message,
            send_notifications=send_notifications)

    def hasBranch(self, branch):
        """See `IBug`."""
        branch = BugBranch.selectOneBy(branch=branch, bug=self)

        return branch is not None

    def linkBranch(self, branch, registrant):
        """See `IBug`."""
        for bug_branch in shortlist(self.linked_branches):
            if bug_branch.branch == branch:
                return bug_branch

        bug_branch = BugBranch(
            branch=branch, bug=self, registrant=registrant)
        branch.date_last_modified = UTC_NOW

        self.addChange(BranchLinkedToBug(UTC_NOW, registrant, branch, self))
        notify(ObjectCreatedEvent(bug_branch))

        return bug_branch

    def unlinkBranch(self, branch, user):
        """See `IBug`."""
        bug_branch = BugBranch.selectOneBy(bug=self, branch=branch)
        if bug_branch is not None:
            self.addChange(BranchUnlinkedFromBug(UTC_NOW, user, branch, self))
            notify(ObjectDeletedEvent(bug_branch, user=user))
            bug_branch.destroySelf()

    def getVisibleLinkedBranches(self, user, eager_load=False):
        """Return all the branches linked to the bug that `user` can see."""
        all_branches = getUtility(IAllBranches)
        linked_branches = list(all_branches.visibleByUser(
            user).linkedToBugs([self]).getBranches(eager_load=eager_load))
        if len(linked_branches) == 0:
            return EmptyResultSet()
        else:
            store = Store.of(self)
            branch_ids = [branch.id for branch in linked_branches]
            return store.find(
                BugBranch,
                BugBranch.bug == self,
                In(BugBranch.branchID, branch_ids))

    @cachedproperty
    def has_cves(self):
        """See `IBug`."""
        return bool(self.cves)

    def linkCVE(self, cve, user):
        """See `IBug`."""
        if cve not in self.cves:
            bugcve = BugCve(bug=self, cve=cve)
            notify(ObjectCreatedEvent(bugcve, user=user))
            return bugcve

    # XXX intellectronica 2008-11-06 Bug #294858:
    # See lp.bugs.interfaces.bug
    def linkCVEAndReturnNothing(self, cve, user):
        """See `IBug`."""
        self.linkCVE(cve, user)
        return None

    def unlinkCVE(self, cve, user):
        """See `IBug`."""
        for cve_link in self.cve_links:
            if cve_link.cve.id == cve.id:
                notify(ObjectDeletedEvent(cve_link, user=user))
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
    completeness_clause = """
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
        pillar = valid_bugtask.pillar
        if (pillar.bug_tracking_usage == ServiceUsage.LAUNCHPAD
            and pillar.answers_usage == ServiceUsage.LAUNCHPAD):
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
            self.newMessage(
                owner=person, subject=self.followup_subject(),
                content=comment)
        notify(
            ObjectModifiedEvent(
                object=bugtask,
                object_before_modification=bugtask_before_modification,
                edited_fields=edited_fields,
                user=person))

        question_target = IQuestionTarget(bugtask.target)
        question = question_target.createQuestionFromBug(self)
        self.addChange(BugConvertedToQuestion(UTC_NOW, person, question))
        get_property_cache(self)._question_from_bug = question
        notify(BugBecameQuestionEvent(self, question, person))
        return question

    @cachedproperty
    def _question_from_bug(self):
        for question in self.questions:
            if (question.ownerID == self.ownerID
                and question.datecreated == self.datecreated):
                return question
        return None

    def getQuestionCreatedFromBug(self):
        """See `IBug`."""
        return self._question_from_bug

    def getMessagesForView(self, slice_info):
        """See `IBug`."""
        # Note that this function and indexed_messages have significant
        # overlap and could stand to be refactored.
        slices = []
        if slice_info is not None:
            # NB: This isn't a full implementation of the slice protocol,
            # merely the bits needed by BugTask:+index.
            for slice in slice_info:
                if not slice.start:
                    assert slice.stop > 0, slice.stop
                    slices.append(BugMessage.index < slice.stop)
                elif not slice.stop:
                    if slice.start < 0:
                        # If the high index is N, a slice of -1: should
                        # return index N - so we need to add one to the
                        # range.
                        slices.append(BugMessage.index >= SQL(
                            "(select max(index) from "
                            "bugmessage where bug=%s) + 1 - %s" % (
                            sqlvalues(self.id, -slice.start))))
                    else:
                        slices.append(BugMessage.index >= slice.start)
                else:
                    slices.append(And(BugMessage.index >= slice.start,
                        BugMessage.index < slice.stop))
        if slices:
            ranges = [Or(*slices)]
        else:
            ranges = []
        # We expect:
        # 1 bugmessage -> 1 message -> small N chunks. For now, using a wide
        # query seems fine as we have to join out from bugmessage anyway.
        result = Store.of(self).find((BugMessage, Message, MessageChunk),
            Message.id == MessageChunk.messageID,
            BugMessage.messageID == Message.id,
            BugMessage.bug == self.id,
            *ranges)
        result.order_by(BugMessage.index, MessageChunk.sequence)

        def eager_load_owners(rows):
            owners = set()
            for row in rows:
                owners.add(row[1].ownerID)
            owners.discard(None)
            if not owners:
                return
            list(PersonSet().getPrecachedPersonsFromIDs(owners,
                need_validity=True))
        return DecoratedResultSet(result, pre_iter_hook=eager_load_owners)

    def addNomination(self, owner, target):
        """See `IBug`."""
        if not self.canBeNominatedFor(target):
            raise NominationError(
                "This bug cannot be nominated for %s." %
                    target.bugtargetdisplayname)

        distroseries = None
        productseries = None
        if IDistroSeries.providedBy(target):
            distroseries = target
            if target.status == SeriesStatus.OBSOLETE:
                raise NominationSeriesObsoleteError(
                    "%s is an obsolete series." % target.bugtargetdisplayname)
        else:
            assert IProductSeries.providedBy(target)
            productseries = target

        if not (check_permission("launchpad.BugSupervisor", target) or
                check_permission("launchpad.Driver", target)):
            raise NominationError(
                "Only bug supervisors or owners can nominate bugs.")

        nomination = BugNomination(
            owner=owner, bug=self, distroseries=distroseries,
            productseries=productseries)
        self.addChange(SeriesNominated(UTC_NOW, owner, target))
        return nomination

    def canBeNominatedFor(self, target):
        """See `IBug`."""
        try:
            self.getNominationFor(target)
        except NotFoundError:
            # No nomination exists. Let's see if the bug is already
            # directly targeted to this nomination target.
            if IDistroSeries.providedBy(target):
                series_getter = operator.attrgetter("distroseries")
                pillar_getter = operator.attrgetter("distribution")
            elif IProductSeries.providedBy(target):
                series_getter = operator.attrgetter("productseries")
                pillar_getter = operator.attrgetter("product")
            else:
                return False

            for task in self.bugtasks:
                if series_getter(task) == target:
                    # The bug is already targeted at this
                    # nomination target.
                    return False

            # No nomination or tasks are targeted at this
            # nomination target. But we also don't want to nominate for a
            # series of a product or distro for which we don't have a
            # plain pillar task.
            for task in self.bugtasks:
                if pillar_getter(task) == pillar_getter(target):
                    return True

            # No tasks match the candidate's pillar. We must refuse.
            return False
        else:
            # The bug is already nominated for this nomination target.
            return False

    def getNominationFor(self, target):
        """See `IBug`."""
        if IDistroSeries.providedBy(target):
            filter_args = dict(distroseriesID=target.id)
        elif IProductSeries.providedBy(target):
            filter_args = dict(productseriesID=target.id)
        else:
            return None

        nomination = BugNomination.selectOneBy(bugID=self.id, **filter_args)

        if nomination is None:
            raise NotFoundError(
                "Bug #%d is not nominated for %s." % (
                self.id, target.displayname))

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
            bug=self, bugtracker=bugtracker, remotebug=str(remote_bug),
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
        notify(ObjectModifiedEvent(
            bugtask, bugtask_before_modification, ['status'], user=user))

        return bugtask

    def setPrivacyAndSecurityRelated(self, private, security_related, who):
        """ See `IBug`."""
        private_changed = False
        security_related_changed = False
        bug_before_modification = Snapshot(self, providing=providedBy(self))

        f_flag_str = 'disclosure.enhanced_private_bug_subscriptions.enabled'
        f_flag = bool(getFeatureFlag(f_flag_str))
        if f_flag:
            # Before we update the privacy or security_related status, we
            # need to reconcile the subscribers to avoid leaking private
            # information.
            if (self.private != private
                    or self.security_related != security_related):
                self.reconcileSubscribers(private, security_related, who)

        if self.private != private:
            private_changed = True
            self.private = private

            if private:
                self.who_made_private = who
                self.date_made_private = UTC_NOW
            else:
                self.who_made_private = None
                self.date_made_private = None

            # XXX: This should be a bulk update. RBC 20100827
            # bug=https://bugs.launchpad.net/storm/+bug/625071
            for attachment in self.attachments_unpopulated:
                attachment.libraryfile.restricted = private

        if self.security_related != security_related:
            security_related_changed = True
            self.security_related = security_related

        if private_changed or security_related_changed:
            # Correct the heat for the bug immediately, so that we don't have
            # to wait for the next calculation job for the adjusted heat.
            self.updateHeat()

        if private_changed or security_related_changed:
            changed_fields = []

            if private_changed:
                changed_fields.append('private')
                if not f_flag and private:
                    # If we didn't call reconcileSubscribers, we may have
                    # bug supervisors who should be on this bug, but aren't.
                    supervisors = set()
                    for bugtask in self.bugtasks:
                        supervisors.add(bugtask.pillar.bug_supervisor)
                    if None in supervisors:
                        supervisors.remove(None)
                    for s in supervisors:
                        subscriptions = get_structural_subscriptions_for_bug(
                                            self, s)
                        if subscriptions != []:
                            self.subscribe(s, who)

            if security_related_changed:
                changed_fields.append('security_related')
                if not f_flag and security_related:
                    # The bug turned out to be security-related, subscribe the
                    # security contact. We do it here only if the feature flag
                    # is not set, otherwise it's done in
                    # reconcileSubscribers().
                    for pillar in self.affected_pillars:
                        if pillar.security_contact is not None:
                            self.subscribe(pillar.security_contact, who)

            notify(ObjectModifiedEvent(
                    self, bug_before_modification, changed_fields, user=who))

        return private_changed, security_related_changed

    def setPrivate(self, private, who):
        """See `IBug`.

        We also record who made the change and when the change took
        place.
        """
        return self.setPrivacyAndSecurityRelated(
            private, self.security_related, who)[0]

    def setSecurityRelated(self, security_related, who):
        """Setter for the `security_related` property."""
        return self.setPrivacyAndSecurityRelated(
            self.private, security_related, who)[1]

    def setAccessPolicy(self, policy):
        """See `IBug`."""
        if policy.pillar != self.default_bugtask.pillar:
            raise UnsuitableAccessPolicyError(
                "Only access policies for %s can be used."
                % self.default_bugtask.pillar.name)
        self.access_policy = policy

    def getRequiredSubscribers(self, for_private, for_security_related, who):
        """Return the mandatory subscribers for a bug with given attributes.

        When a bug is marked as private or security related, it is required
        that certain people be subscribed so they can access details about the
        bug. The rules are:
            security=true, private=true/false ->
                subscribers = the reporter + security contact for each task
            security=false, private=true ->
                subscribers = the reporter + bug supervisor for each task
            security=false, private=false ->
                subscribers = ()

        If bug supervisor or security contact is unset, fallback to bugtask
        reporter/owner.
        """
        if not for_private and not for_security_related:
            return set()
        result = set()
        result.add(self.owner)
        for bugtask in self.bugtasks:
            maintainer = bugtask.pillar.owner
            if for_security_related:
                result.add(bugtask.pillar.security_contact or maintainer)
            if for_private:
                result.add(bugtask.pillar.bug_supervisor or maintainer)
        if for_private:
            subscribers_for_who = self.getSubscribersForPerson(who)
            if subscribers_for_who.is_empty():
                result.add(who)
        return result

    def getAutoRemovedSubscribers(self, for_private, for_security_related):
        """Return the to be removed subscribers for bug with given attributes.

        When a bug's privacy or security related attributes change, some
        existing subscribers may need to be automatically removed.
        The rules are:
            security=false ->
                auto removed subscribers = (bugtask security contacts)
            privacy=false ->
                auto removed subscribers = (bugtask bug supervisors)

        """
        bug_supervisors = []
        security_contacts = []
        for pillar in self.affected_pillars:
            if (self.security_related and not for_security_related
                and pillar.security_contact):
                    security_contacts.append(pillar.security_contact)
            if (self.private and not for_private
                and pillar.bug_supervisor):
                    bug_supervisors.append(pillar.bug_supervisor)
        return bug_supervisors, security_contacts

    def reconcileSubscribers(self, for_private, for_security_related, who):
        """ Ensure only appropriate people are subscribed to private bugs.

        When a bug is marked as either private = True or security_related =
        True, we need to ensure that only people who are authorised to know
        about the privileged contents of the bug remain directly subscribed
        to it. So we:
          1. Get the required subscribers depending on the bug status.
          2. Get the auto removed subscribers depending on the bug status.
             eg security contacts when a bug is updated to security related =
             false.
          3. Get the allowed subscribers = required subscribers
                                            + bugtask owners
          4. Remove any current direct subscribers who are not allowed or are
             to be auto removed.
          5. Add any subscribers who are required.
        """
        current_direct_subscribers = (
            self.getSubscriptionInfo().direct_subscribers)
        required_subscribers = self.getRequiredSubscribers(
            for_private, for_security_related, who)
        removed_bug_supervisors, removed_security_contacts = (
            self.getAutoRemovedSubscribers(for_private, for_security_related))
        for subscriber in removed_bug_supervisors:
            recipients = BugNotificationRecipients()
            recipients.addBugSupervisor(subscriber)
            notification_text = ("This bug is no longer private so the bug "
                "supervisor was unsubscribed. They will no longer be "
                "notified of changes to this bug for privacy related "
                "reasons, but may receive notifications about this bug from "
                "other subscriptions.")
            self.unsubscribe(
                subscriber, who, ignore_permissions=True,
                send_notification=True,
                notification_text=notification_text,
                recipients=recipients)
        for subscriber in removed_security_contacts:
            recipients = BugNotificationRecipients()
            recipients.addSecurityContact(subscriber)
            notification_text = ("This bug is no longer security related so "
                "the security contact was unsubscribed. They will no longer "
                "be notified of changes to this bug for security related "
                "reasons, but may receive notifications about this bug "
                "from other subscriptions.")
            self.unsubscribe(
                subscriber, who, ignore_permissions=True,
                send_notification=True,
                notification_text=notification_text,
                recipients=recipients)

        # If this bug is for a project that is marked as having private bugs
        # by default, and the bug is private or security related, we will
        # unsubscribe any unauthorised direct subscribers.
        pillar = self.default_bugtask.pillar
        private_project = IProduct.providedBy(pillar) and pillar.private_bugs
        if private_project and (for_private or for_security_related):
            allowed_subscribers = set()
            allowed_subscribers.add(self.owner)
            for bugtask in self.bugtasks:
                allowed_subscribers.add(bugtask.owner)
                allowed_subscribers.add(bugtask.pillar.owner)
                allowed_subscribers.update(set(bugtask.pillar.drivers))
            allowed_subscribers = required_subscribers.union(
                allowed_subscribers)
            subscribers_to_remove = (
                current_direct_subscribers.difference(allowed_subscribers))
            for subscriber in subscribers_to_remove:
                self.unsubscribe(subscriber, who, ignore_permissions=True)

        subscribers_to_add = (
            required_subscribers.difference(current_direct_subscribers))
        for subscriber in subscribers_to_add:
            self.subscribe(subscriber, who)

    def getBugTask(self, target):
        """See `IBug`."""
        for bugtask in self.bugtasks:
            if bugtask.target == target:
                return bugtask

        return None

    def _getTags(self):
        """Get the tags as a sorted list of strings."""
        return self._cached_tags

    @cachedproperty
    def _cached_tags(self):
        return list(Store.of(self).find(
            BugTag.tag,
            BugTag.bugID == self.id).order_by(BugTag.tag))

    def _setTags(self, tags):
        """Set the tags from a list of strings."""
        # Sets provide an easy way to get the difference between the old and
        # new tags.
        new_tags = set([tag.lower() for tag in tags])
        old_tags = set(self.tags)
        # The cache will be stale after we add/remove tags, clear it.
        del get_property_cache(self)._cached_tags
        # Find the set of tags that are to be removed and remove them.
        removed_tags = old_tags.difference(new_tags)
        for removed_tag in removed_tags:
            tag = BugTag.selectOneBy(bug=self, tag=removed_tag)
            tag.destroySelf()
        # Find the set of tags that are to be added and add them.
        added_tags = new_tags.difference(old_tags)
        for added_tag in added_tags:
            BugTag(bug=self, tag=added_tag)
        # Write all pending changes to the DB, including any pending non-tag
        # changes.
        Store.of(self).flush()

    tags = property(_getTags, _setTags)

    @staticmethod
    def getBugTasksByPackageName(bugtasks):
        """See IBugTask."""
        bugtasks_by_package = {}
        for bugtask in bugtasks:
            bugtasks_by_package.setdefault(bugtask.sourcepackagename, [])
            bugtasks_by_package[bugtask.sourcepackagename].append(bugtask)
        return bugtasks_by_package

    def _getAffectedUser(self, user):
        """Return the `IBugAffectsPerson` for a user, or None

        :param user: An `IPerson` that may be affected by the bug.
        :return: An `IBugAffectsPerson` or None.
        """
        if user is None:
            return None
        else:
            return Store.of(self).get(
                BugAffectsPerson, (self.id, user.id))

    def isUserAffected(self, user):
        """See `IBug`."""
        bap = self._getAffectedUser(user)
        if bap is not None:
            return bap.affected
        else:
            return None

    def _flushAndInvalidate(self):
        """Flush all changes to the store and re-read `self` from the DB."""
        store = Store.of(self)
        store.flush()
        store.invalidate(self)

    def shouldConfirmBugtasks(self):
        """Should we try to confirm this bug's bugtasks?
        The answer is yes if more than one user is affected."""
        # == 2 would probably be sufficient once we have all legacy bug tasks
        # confirmed.  For now, this is a compromise: we don't need a migration
        # step, but we will make some unnecessary comparisons.
        return self.users_affected_count_with_dupes > 1

    def maybeConfirmBugtasks(self):
        """Maybe try to confirm our new bugtasks."""
        if self.shouldConfirmBugtasks():
            for bugtask in self.bugtasks:
                bugtask.maybeConfirm()

    def markUserAffected(self, user, affected=True):
        """See `IBug`."""
        bap = self._getAffectedUser(user)
        if bap is None:
            BugAffectsPerson(bug=self, person=user, affected=affected)
            self._flushAndInvalidate()
        else:
            if bap.affected != affected:
                bap.affected = affected
                self._flushAndInvalidate()

        # Loop over dupes.
        for dupe in self.duplicates:
            if dupe._getAffectedUser(user) is not None:
                dupe.markUserAffected(user, affected)

        if affected:
            self.maybeConfirmBugtasks()

        self.updateHeat()

    def _markAsDuplicate(self, duplicate_of):
        """Mark this bug as a duplicate of another.

        Marking a bug as a duplicate requires a recalculation
        of the heat of this bug and of the master bug, and it
        requires a recalulation of the heat cache of the
        affected bug targets. None of this is done here in order
        to avoid unnecessary repetitions in recursive calls
        for duplicates of this bug, which also become duplicates
        of the new master bug.
        """
        affected_targets = set()
        field = DuplicateBug()
        field.context = self
        current_duplicateof = self.duplicateof
        try:
            if duplicate_of is not None:
                field._validate(duplicate_of)
            if self.duplicates:
                user = getUtility(ILaunchBag).user
                for duplicate in self.duplicates:
                    old_value = duplicate.duplicateof
                    affected_targets.update(
                        duplicate._markAsDuplicate(duplicate_of))

                    # Put an entry into the BugNotification table for
                    # later processing.
                    change = BugDuplicateChange(
                        when=None, person=user,
                        what_changed='duplicateof',
                        old_value=old_value,
                        new_value=duplicate_of)
                    empty_recipients = BugNotificationRecipients()
                    duplicate.addChange(
                        change, empty_recipients, deferred=True)

            self.duplicateof = duplicate_of
        except LaunchpadValidationError, validation_error:
            raise InvalidDuplicateValue(validation_error)
        if duplicate_of is not None:
            # Update the heat of the master bug and set this bug's heat
            # to 0 (since it's a duplicate, it shouldn't have any heat
            # at all).
            self.setHeat(0, affected_targets=affected_targets)
            # Maybe confirm bug tasks, now that more people might be affected
            # by this bug from the duplicates.
            duplicate_of.maybeConfirmBugtasks()
        else:
            # Otherwise, recalculate this bug's heat, since it will be 0
            # from having been a duplicate. We also update the bug that
            # was previously duplicated.
            self.updateHeat(affected_targets)
            if current_duplicateof is not None:
                current_duplicateof.updateHeat(affected_targets)
        return affected_targets

    def markAsDuplicate(self, duplicate_of):
        """See `IBug`."""
        affected_targets = self._markAsDuplicate(duplicate_of)
        if duplicate_of is not None:
            duplicate_of.updateHeat(affected_targets)
        for target in affected_targets:
            target.recalculateBugHeatCache()

    def setCommentVisibility(self, user, comment_number, visible):
        """See `IBug`."""
        bug_message_set = getUtility(IBugMessageSet)
        bug_message = bug_message_set.getByBugAndMessage(
            self, self.messages[comment_number])
        bug_message.message.visible = visible

    @cachedproperty
    def _known_viewers(self):
        """A set of known persons able to view this bug.

        This method must return an empty set or bug searches will trigger late
        evaluation. Any 'should be set on load' propertis must be done by the
        bug search.

        If you are tempted to change this method, don't. Instead see
        userCanView which defines the just-in-time policy for bug visibility,
        and BugTask._search which honours visibility rules.
        """
        return set()

    def userCanView(self, user):
        """See `IBug`.

        This method is called by security adapters but only in the case for
        authenticated users.  It is also called in other contexts where the
        user may be anonymous.

        If bug privacy rights are changed here, corresponding changes need
        to be made to the queries which screen for privacy.  See
        Bug.searchAsUser and BugTask.get_bug_privacy_filter_with_decorator.
        """
        if not self.private:
            # This is a public bug.
            return True
        # This method may be called for anonymous users.  For private bugs
        # always return false for anonymous.
        if user is None:
            return False
        if user.id in self._known_viewers:
            return True

        elif IPersonRoles(user).in_admin:
            # Admins can view all bugs.
            return True
        else:
            # At this point we know the bug is private and the user is
            # unprivileged.

            # Assignees to bugtasks can see the private bug.
            for bugtask in self.bugtasks:
                if user.inTeam(bugtask.assignee):
                    self._known_viewers.add(user.id)
                    return True
            # Explicit subscribers may also view it.
            for subscription in self.subscriptions:
                if user.inTeam(subscription.person):
                    self._known_viewers.add(user.id)
                    return True
            # Pillar owners can view it. Note that this is contentious and
            # possibly incorrect: see bug 702429.
            for pillar_owner in [bt.pillar.owner for bt in self.bugtasks]:
                if user.inTeam(pillar_owner):
                    self._known_viewers.add(user.id)
                    return True
        return False

    def linkHWSubmission(self, submission):
        """See `IBug`."""
        getUtility(IHWSubmissionBugSet).create(submission, self)

    def unlinkHWSubmission(self, submission):
        """See `IBug`."""
        getUtility(IHWSubmissionBugSet).remove(submission, self)

    def getHWSubmissions(self, user=None):
        """See `IBug`."""
        return getUtility(IHWSubmissionBugSet).submissionsForBug(self, user)

    def personIsDirectSubscriber(self, person):
        """See `IBug`."""
        if person in self._subscriber_cache:
            return True
        if person in self._unsubscribed_cache:
            return False
        if person is None:
            return False
        store = Store.of(self)
        subscriptions = store.find(
            BugSubscription,
            BugSubscription.bug == self,
            BugSubscription.person == person)
        return not subscriptions.is_empty()

    def personIsAlsoNotifiedSubscriber(self, person):
        """See `IBug`."""
        # We have to use getAlsoNotifiedSubscribers() here and iterate
        # over what it returns because "also notified subscribers" is
        # actually a composite of bug contacts, structural subscribers
        # and assignees. As such, it's not possible to get them all with
        # one query.
        also_notified_subscribers = self.getAlsoNotifiedSubscribers()
        if person in also_notified_subscribers:
            return True
        # Otherwise check to see if the person is a member of any of the
        # subscribed teams.
        for subscriber in also_notified_subscribers:
            if subscriber.is_team and person.inTeam(subscriber):
                return True
        return False

    def personIsSubscribedToDuplicate(self, person):
        """See `IBug`."""
        if person in self._subscriber_dups_cache:
            return True
        if person in self._unsubscribed_cache:
            return False
        if person is None:
            return False
        store = Store.of(self)
        subscriptions_from_dupes = store.find(
            BugSubscription,
            Bug.duplicateof == self,
            BugSubscription.bug_id == Bug.id,
            BugSubscription.person == person)

        return not subscriptions_from_dupes.is_empty()

    def setHeat(self, heat, timestamp=None, affected_targets=None):
        """See `IBug`."""
        """See `IBug`."""
        if timestamp is None:
            timestamp = UTC_NOW

        if heat < 0:
            heat = 0

        self.heat = heat
        self.heat_last_updated = timestamp
        if affected_targets is None:
            for task in self.bugtasks:
                task.target.recalculateBugHeatCache()
        else:
            affected_targets.update(task.target for task in self.bugtasks)

    def updateHeat(self, affected_targets=None):
        """See `IBug`."""
        if self.duplicateof is not None:
            # If this bug is a duplicate we don't try to calculate its
            # heat.
            return

        # We need to flush the store first to ensure that changes are
        # reflected in the new bug heat total.
        store = Store.of(self)
        store.flush()

        self.heat = SQL("calculate_bug_heat(%s)" % sqlvalues(self))
        self.heat_last_updated = UTC_NOW
        if affected_targets is None:
            for task in self.bugtasks:
                task.target.recalculateBugHeatCache()
        else:
            affected_targets.update(task.target for task in self.bugtasks)
        store.flush()

    def _attachments_query(self):
        """Helper for the attachments* properties."""
        # bug attachments with no LibraryFileContent have been deleted - the
        # garbo_daily run will remove the LibraryFileAlias asynchronously.
        # See bug 542274 for more details.
        store = Store.of(self)
        return store.find(
            (BugAttachment, LibraryFileAlias, LibraryFileContent),
            BugAttachment.bug == self,
            BugAttachment.libraryfileID == LibraryFileAlias.id,
            LibraryFileContent.id == LibraryFileAlias.contentID,
            ).order_by(BugAttachment.id)

    @property
    def attachments(self):
        """See `IBug`.

        This property does eager loading of the index_messages so that
        the API which wants the message_link for the attachment can
        answer that without O(N^2) overhead. As such it is moderately
        expensive to call (it currently retrieves all messages before
        any attachments, and does this when attachments is evaluated,
        not when the resultset is processed).
        """
        message_to_indexed = {}
        for message in self._indexed_messages(include_parents=False):
            message_to_indexed[message.id] = message

        def set_indexed_message(row):
            attachment = row[0]
            # row[1] - the LibraryFileAlias is now in the storm cache and
            # will be found without a query when dereferenced.
            indexed_message = message_to_indexed.get(attachment._messageID)
            if indexed_message is not None:
                get_property_cache(attachment).message = indexed_message
            return attachment
        rawresults = self._attachments_query()
        return DecoratedResultSet(rawresults, set_indexed_message)

    @property
    def attachments_unpopulated(self):
        """See `IBug`.

        This version does not pre-lookup messages and LibraryFileAliases.

        The regular 'attachments' property does prepopulation because it is
        exposed in the API.
        """
        # Grab the attachment only; the LibraryFileAlias will be eager loaded.
        return DecoratedResultSet(
            self._attachments_query(),
            operator.itemgetter(0))

    def getActivityForDateRange(self, start_date, end_date):
        """See `IBug`."""
        store = Store.of(self)
        activity_in_range = store.find(
            BugActivity,
            BugActivity.bug == self,
            BugActivity.datechanged >= start_date,
            BugActivity.datechanged <= end_date)
        return activity_in_range


@ProxyFactory
def get_also_notified_subscribers(
    bug_or_bugtask, recipients=None, level=None):
    """Return the indirect subscribers for a bug or bug task.

    Return the list of people who should get notifications about changes
    to the bug or task because of having an indirect subscription
    relationship with it (by subscribing to a target, being an assignee
    or owner, etc...)

    If `recipients` is present, add the subscribers to the set of
    bug notification recipients.
    """
    if IBug.providedBy(bug_or_bugtask):
        bug = bug_or_bugtask
        bugtasks = bug.bugtasks
    elif IBugTask.providedBy(bug_or_bugtask):
        bug = bug_or_bugtask.bug
        bugtasks = [bug_or_bugtask]
    else:
        raise ValueError('First argument must be bug or bugtask')

    if bug.private:
        return []

    # Direct subscriptions always take precedence over indirect
    # subscriptions.
    direct_subscribers = set(bug.getDirectSubscribers())

    also_notified_subscribers = set()

    for bugtask in bugtasks:
        if (bugtask.assignee and
            bugtask.assignee not in direct_subscribers):
            # We have an assignee that is not a direct subscriber.
            also_notified_subscribers.add(bugtask.assignee)
            if recipients is not None:
                recipients.addAssignee(bugtask.assignee)

        # If the target's bug supervisor isn't set...
        pillar = bugtask.pillar
        if (pillar.bug_supervisor is None and
            pillar.official_malone and
            pillar.owner not in direct_subscribers):
            # ...we add the owner as a subscriber.
            also_notified_subscribers.add(pillar.owner)
            if recipients is not None:
                recipients.addRegistrant(pillar.owner, pillar)

    # This structural subscribers code omits direct subscribers itself.
    also_notified_subscribers.update(
        get_structural_subscribers(
            bug_or_bugtask, recipients, level, direct_subscribers))

    # Remove security proxy for the sort key, but return
    # the regular proxied object.
    return sorted(also_notified_subscribers,
                  key=lambda x: removeSecurityProxy(x).displayname)


def load_people(*where):
    """Get subscribers from subscriptions.

    Also preloads `ValidPersonCache` records if they exist.

    :param people: An iterable sequence of `Person` IDs.
    :return: A `DecoratedResultSet` of `Person` objects. The corresponding
        `ValidPersonCache` records are loaded simultaneously.
    """
    return PersonSet()._getPrecachedPersons(
        origin=[Person], conditions=where, need_validity=True)


class BugSubscriberSet(frozenset):
    """A set of bug subscribers

    Every member should provide `IPerson`.
    """

    @cachedproperty
    def sorted(self):
        """A sorted tuple of this set's members.

        Sorted with `person_sort_key`, the default sort key for `Person`.
        """
        return tuple(sorted(self, key=person_sort_key))


class BugSubscriptionSet(frozenset):
    """A set of bug subscriptions."""

    @cachedproperty
    def sorted(self):
        """A sorted tuple of this set's members.

        Sorted with `person_sort_key` of the subscription owner.
        """
        self.subscribers  # Pre-load subscribers.
        sort_key = lambda sub: person_sort_key(sub.person)
        return tuple(sorted(self, key=sort_key))

    @cachedproperty
    def subscribers(self):
        """A `BugSubscriberSet` of the owners of this set's members."""
        if len(self) == 0:
            return BugSubscriberSet()
        else:
            condition = Person.id.is_in(
                removeSecurityProxy(subscription).person_id
                for subscription in self)
            return BugSubscriberSet(load_people(condition))


class StructuralSubscriptionSet(frozenset):
    """A set of structural subscriptions."""

    @cachedproperty
    def sorted(self):
        """A sorted tuple of this set's members.

        Sorted with `person_sort_key` of the subscription owner.
        """
        self.subscribers  # Pre-load subscribers.
        sort_key = lambda sub: person_sort_key(sub.subscriber)
        return tuple(sorted(self, key=sort_key))

    @cachedproperty
    def subscribers(self):
        """A `BugSubscriberSet` of the owners of this set's members."""
        if len(self) == 0:
            return BugSubscriberSet()
        else:
            condition = Person.id.is_in(
                removeSecurityProxy(subscription).subscriberID
                for subscription in self)
            return BugSubscriberSet(load_people(condition))


# XXX: GavinPanella 2010-12-08 bug=694057: Subclasses of frozenset don't
# appear to be granted those permissions given to frozenset. This would make
# writing ZCML tedious, so I've opted for registering custom checkers (see
# lp_sitecustomize for some other jiggery pokery in the same vein) while I
# seek a better solution.
from zope.security import checker
checker_for_frozen_set = checker.getCheckerForInstancesOf(frozenset)
checker_for_subscriber_set = checker.NamesChecker(["sorted"])
checker_for_subscription_set = checker.NamesChecker(["sorted", "subscribers"])
checker.BasicTypes[BugSubscriberSet] = checker.MultiChecker(
    (checker_for_frozen_set.get_permissions,
     checker_for_subscriber_set.get_permissions))
checker.BasicTypes[BugSubscriptionSet] = checker.MultiChecker(
    (checker_for_frozen_set.get_permissions,
     checker_for_subscription_set.get_permissions))
checker.BasicTypes[StructuralSubscriptionSet] = checker.MultiChecker(
    (checker_for_frozen_set.get_permissions,
     checker_for_subscription_set.get_permissions))


def freeze(factory):
    """Return a decorator that wraps returned values with `factory`."""

    def decorate(func):
        """Decorator that wraps returned values."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            return factory(func(*args, **kwargs))
        return wrapper

    return decorate


class BugSubscriptionInfo:
    """Represents bug subscription sets.

    The intention for this class is to encapsulate all calculations of
    subscriptions and subscribers for a bug. Some design considerations:

    * Immutable.

    * Set-based.

    * Sets are cached.

    * Usable with a *snapshot* of a bug. This is interesting for two reasons:

      - Event subscribers commonly deal with snapshots. An instance of this
        class could be added to a custom snapshot so that multiple subscribers
        can share the information it contains.

      - Use outside of the web request. A serialized snapshot could be used to
        calculate subscribers for a particular bug state. This could help us
        to move even more bug mail processing out of the web request.

    """

    implements(IHasBug)

    def __init__(self, bug, level):
        self.bug = bug
        assert level is not None
        self.level = level

    @cachedproperty
    @freeze(BugSubscriptionSet)
    def old_direct_subscriptions(self):
        """The bug's direct subscriptions."""
        return IStore(BugSubscription).find(
            BugSubscription,
            BugSubscription.bug_notification_level >= self.level,
            BugSubscription.bug == self.bug,
            Not(In(BugSubscription.person_id,
                   Select(BugMute.person_id, BugMute.bug_id == self.bug.id))))

    @cachedproperty
    def direct_subscriptions_and_subscribers(self):
        """The bug's direct subscriptions."""
        res = IStore(BugSubscription).find(
            (BugSubscription, Person),
            BugSubscription.bug_notification_level >= self.level,
            BugSubscription.bug == self.bug,
            BugSubscription.person_id == Person.id,
            Not(In(BugSubscription.person_id,
                   Select(BugMute.person_id,
                          BugMute.bug_id == self.bug.id))))
        # Here we could test for res.count() but that will execute another
        # query.  This structure avoids the extra query.
        return zip(*res) or ((), ())

    @cachedproperty
    @freeze(BugSubscriptionSet)
    def direct_subscriptions(self):
        return self.direct_subscriptions_and_subscribers[0]

    @cachedproperty
    @freeze(BugSubscriberSet)
    def direct_subscribers(self):
        return self.direct_subscriptions_and_subscribers[1]

    @cachedproperty
    def duplicate_subscriptions_and_subscribers(self):
        """Subscriptions to duplicates of the bug."""
        if self.bug.private:
            return ((), ())
        else:
            res = IStore(BugSubscription).find(
                (BugSubscription, Person),
                BugSubscription.bug_notification_level >= self.level,
                BugSubscription.bug_id == Bug.id,
                BugSubscription.person_id == Person.id,
                Bug.duplicateof == self.bug,
                Not(In(BugSubscription.person_id,
                       Select(BugMute.person_id, BugMute.bug_id == Bug.id))))
        # Here we could test for res.count() but that will execute another
        # query.  This structure avoids the extra query.
        return zip(*res) or ((), ())

    @cachedproperty
    @freeze(BugSubscriptionSet)
    def duplicate_subscriptions(self):
        return self.duplicate_subscriptions_and_subscribers[0]

    @cachedproperty
    @freeze(BugSubscriberSet)
    def duplicate_subscribers(self):
        return self.duplicate_subscriptions_and_subscribers[1]

    @cachedproperty
    @freeze(BugSubscriptionSet)
    def duplicate_only_subscriptions(self):
        """Subscriptions to duplicates of the bug.

        Excludes subscriptions for people who have a direct subscription or
        are also notified for another reason.
        """
        self.duplicate_subscribers  # Pre-load subscribers.
        higher_precedence = (
            self.direct_subscribers.union(
                self.also_notified_subscribers))
        return (
            subscription for subscription in self.duplicate_subscriptions
            if subscription.person not in higher_precedence)

    @cachedproperty
    @freeze(StructuralSubscriptionSet)
    def structural_subscriptions(self):
        """Structural subscriptions to the bug's targets."""
        return list(get_structural_subscriptions_for_bug(self.bug))

    @cachedproperty
    @freeze(BugSubscriberSet)
    def all_assignees(self):
        """Assignees of the bug's tasks."""
        assignees = Select(BugTask.assigneeID, BugTask.bug == self.bug)
        return load_people(Person.id.is_in(assignees))

    @cachedproperty
    @freeze(BugSubscriberSet)
    def all_pillar_owners_without_bug_supervisors(self):
        """Owners of pillars for which no Bug supervisor is configured."""
        for bugtask in self.bug.bugtasks:
            pillar = bugtask.pillar
            if pillar.bug_supervisor is None:
                yield pillar.owner

    @cachedproperty
    def also_notified_subscribers(self):
        """All subscribers except direct and dupe subscribers."""
        if self.bug.private:
            return BugSubscriberSet()
        else:
            muted = IStore(BugMute).find(
                Person,
                BugMute.person_id == Person.id,
                BugMute.bug == self.bug)
            return BugSubscriberSet().union(
                self.structural_subscriptions.subscribers,
                self.all_pillar_owners_without_bug_supervisors,
                self.all_assignees).difference(
                self.direct_subscribers).difference(muted)

    @cachedproperty
    def indirect_subscribers(self):
        """All subscribers except direct subscribers."""
        return self.also_notified_subscribers.union(
            self.duplicate_subscribers)


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

        privacy_filter = get_bug_privacy_filter(user)
        if privacy_filter:
            where_clauses.append(privacy_filter)

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

    def createBug(self, bug_params, notify_event=True):
        """See `IBugSet`."""
        # Make a copy of the parameter object, because we might modify some
        # of its attribute values below.
        params = snapshot_bug_params(bug_params)

        if params.product and params.product.private_bugs:
            # If the private_bugs flag is set on a product, then
            # force the new bug report to be private.
            params.private = True

        bug, event = self.createBugWithoutTarget(params)

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

        # Create the task on a product if one was passed.
        if params.product:
            getUtility(IBugTaskSet).createTask(
                bug, params.owner, params.product, status=params.status)

        # Create the task on a source package name if one was passed.
        if params.distribution:
            target = params.distribution
            if params.sourcepackagename:
                target = target.getSourcePackage(params.sourcepackagename)
            getUtility(IBugTaskSet).createTask(
                bug, params.owner, target, status=params.status)

        bug_task = bug.default_bugtask
        if params.assignee:
            bug_task.transitionToAssignee(params.assignee)
        if params.importance:
            bug_task.transitionToImportance(params.importance, params.owner)
        if params.milestone:
            bug_task.transitionToMilestone(params.milestone, params.owner)

        # Tell everyone.
        if notify_event:
            notify(event)

        # Calculate the bug's initial heat.
        bug.updateHeat()

        if not notify_event:
            return bug, event
        return bug

    def createBugWithoutTarget(self, bug_params):
        """See `IBugSet`."""
        # Make a copy of the parameter object, because we might modify some
        # of its attribute values below.
        params = snapshot_bug_params(bug_params)

        if not (params.comment or params.description or params.msg):
            raise AssertionError(
                'Either comment, msg, or description should be specified.')

        if not params.datecreated:
            params.datecreated = UTC_NOW

        # make sure we did not get TOO MUCH information
        assert params.comment is None or params.msg is None, (
            "Expected either a comment or a msg, but got both.")

        # Create the bug comment if one was given.
        if params.comment:
            rfc822msgid = make_msgid('malonedeb')
            params.msg = Message(
                subject=params.title, rfc822msgid=rfc822msgid,
                owner=params.owner, datecreated=params.datecreated)
            MessageChunk(
                message=params.msg, sequence=1, content=params.comment,
                blob=None)

        # Extract the details needed to create the bug and optional msg.
        if not params.description:
            params.description = params.msg.text_contents

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

        if params.subscribe_owner:
            bug.subscribe(params.owner, params.owner)
        if params.tags:
            bug.tags = params.tags

        # Subscribe other users.
        for subscriber in params.subscribers:
            bug.subscribe(subscriber, params.owner)

        # Link the bug to the message.
        BugMessage(bug=bug, message=params.msg, index=0)

        # Mark the bug reporter as affected by that bug.
        bug.markUserAffected(bug.owner)

        if params.cve is not None:
            bug.linkCVE(params.cve, params.owner)

        # Populate the creation event.
        if params.filed_by is None:
            event = ObjectCreatedEvent(bug, user=params.owner)
        else:
            event = ObjectCreatedEvent(bug, user=params.filed_by)

        return (bug, event)

    def getDistinctBugsForBugTasks(self, bug_tasks, user, limit=10):
        """See `IBugSet`."""
        # XXX: Graham Binns 2009-05-28 bug=75764
        #      We slice bug_tasks here to prevent this method from
        #      causing timeouts, since if we try to iterate over it
        #      Transaction.iterSelect() will try to listify the results.
        #      This can be fixed by selecting from Bugs directly, but
        #      that's non-trivial.
        # ---: Robert Collins 2010-08-18: if bug_tasks implements IResultSet
        #      then it should be very possible to improve on it, though
        #      DecoratedResultSets would need careful handling (e.g. type
        #      driven callbacks on columns)
        # We select more than :limit: since if a bug affects more than
        # one source package, it will be returned more than one time. 4
        # is an arbitrary number that should be large enough.
        bugs = []
        for bug_task in bug_tasks[:4 * limit]:
            bug = bug_task.bug
            duplicateof = bug.duplicateof
            if duplicateof is not None:
                bug = duplicateof

            if not bug.userCanView(user):
                continue

            if bug not in bugs:
                bugs.append(bug)
                if len(bugs) >= limit:
                    break

        return bugs

    def getByNumbers(self, bug_numbers):
        """See `IBugSet`."""
        if bug_numbers is None or len(bug_numbers) < 1:
            return EmptyResultSet()
        store = IStore(Bug)
        result_set = store.find(Bug, Bug.id.is_in(bug_numbers))
        return result_set.order_by('id')

    def dangerousGetAllBugs(self):
        """See `IBugSet`."""
        store = IStore(Bug)
        result_set = store.find(Bug)
        return result_set.order_by('id')

    def getBugsWithOutdatedHeat(self, max_heat_age):
        """See `IBugSet`."""
        store = IStore(Bug)
        last_updated_cutoff = (
            datetime.now(timezone('UTC')) -
            timedelta(days=max_heat_age))
        last_updated_clause = Or(
            Bug.heat_last_updated < last_updated_cutoff,
            Bug.heat_last_updated == None)

        return store.find(
            Bug, Bug.duplicateof == None, last_updated_clause).order_by('id')


class BugAffectsPerson(SQLBase):
    """A bug is marked as affecting a user."""
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    affected = BoolCol(notNull=True, default=True)
    __storm_primary__ = "bugID", "personID"


class FileBugData:
    """Extra data to be added to the bug."""
    implements(IFileBugData)

    def __init__(self, initial_summary=None, initial_tags=None,
                 private=None, subscribers=None, extra_description=None,
                 comments=None, attachments=None,
                 hwdb_submission_keys=None):
        if initial_tags is None:
            initial_tags = []
        if subscribers is None:
            subscribers = []
        if comments is None:
            comments = []
        if attachments is None:
            attachments = []
        if hwdb_submission_keys is None:
            hwdb_submission_keys = []

        self.initial_summary = initial_summary
        self.private = private
        self.extra_description = extra_description
        self.initial_tags = initial_tags
        self.subscribers = subscribers
        self.comments = comments
        self.attachments = attachments
        self.hwdb_submission_keys = hwdb_submission_keys

    def asDict(self):
        """Return the FileBugData instance as a dict."""
        return self.__dict__.copy()


class BugMute(StormBase):
    """Contains bugs a person has decided to block notifications from."""

    implements(IBugMute)

    __storm_table__ = "BugMute"

    def __init__(self, person=None, bug=None):
        if person is not None:
            self.person = person
        if bug is not None:
            self.bug_id = bug.id

    person_id = Int("person", allow_none=False, validator=validate_person)
    person = Reference(person_id, "Person.id")

    bug_id = Int("bug", allow_none=False)
    bug = Reference(bug_id, "Bug.id")

    __storm_primary__ = 'person_id', 'bug_id'

    date_created = DateTime(
        "date_created", allow_none=False, default=UTC_NOW,
        tzinfo=pytz.UTC)
