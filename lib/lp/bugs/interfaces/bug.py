# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213,E0602

"""Interfaces related to bugs."""

__metaclass__ = type

__all__ = [
    'CreateBugParams',
    'CreatedBugWithNoBugTasksError',
    'IBug',
    'IBugAddForm',
    'IBugBecameQuestionEvent',
    'IBugDelta',
    'IBugMute',
    'IBugSet',
    'IFileBugData',
    'IFrontPageBugAddForm',
    'IProjectGroupBugAddForm',
    ]

from lazr.enum import DBEnumeratedType

from lazr.lifecycle.snapshot import doNotSnapshot
from lazr.restful.declarations import (
    accessor_for,
    call_with,
    export_as_webservice_entry,
    export_factory_operation,
    export_operation_as,
    export_read_operation,
    export_write_operation,
    exported,
    mutator_for,
    operation_for_version,
    operation_parameters,
    operation_returns_collection_of,
    operation_returns_entry,
    rename_parameters_as,
    REQUEST_USER,
    )
from lazr.restful.fields import (
    CollectionField,
    Reference,
    )
from lazr.restful.interface import copy_field
from zope.component import getUtility
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Bytes,
    Choice,
    Datetime,
    Int,
    List,
    Object,
    Text,
    TextLine,
    )
from zope.schema.vocabulary import SimpleVocabulary

from canonical.launchpad import _
from canonical.launchpad.interfaces.launchpad import IPrivacy
from lp.services.messages.interfaces.message import IMessage
from lp.app.validators.attachment import attachment_size_constraint
from lp.app.validators.name import bug_name_validator
from lp.app.errors import NotFoundError
from lp.bugs.interfaces.bugactivity import IBugActivity
from lp.bugs.interfaces.bugattachment import IBugAttachment
from lp.bugs.interfaces.bugbranch import IBugBranch
from lp.bugs.interfaces.bugtask import (
    BugTaskImportance,
    BugTaskStatus,
    IBugTask,
    )
from lp.bugs.interfaces.bugwatch import IBugWatch
from lp.bugs.interfaces.cve import ICve
from lp.code.interfaces.branchlink import IHasLinkedBranches
from lp.registry.interfaces.person import IPerson
from lp.services.fields import (
    BugField,
    ContentNameField,
    Description,
    DuplicateBug,
    PersonChoice,
    PublicPersonChoice,
    Tag,
    Title,
    )


class CreateBugParams:
    """The parameters used to create a bug."""

    def __init__(self, owner, title, comment=None, description=None, msg=None,
                 status=None, datecreated=None, security_related=False,
                 private=False, subscribers=(),
                 tags=None, subscribe_owner=True, filed_by=None,
                 importance=None, milestone=None, assignee=None, cve=None):
        self.owner = owner
        self.title = title
        self.comment = comment
        self.description = description
        self.msg = msg
        self.status = status
        self.datecreated = datecreated
        self.security_related = security_related
        self.private = private
        self.subscribers = subscribers
        self.product = None
        self.distribution = None
        self.sourcepackagename = None
        self.tags = tags
        self.subscribe_owner = subscribe_owner
        self.filed_by = filed_by
        self.importance = importance
        self.milestone = milestone
        self.assignee = assignee
        self.cve = cve

    def setBugTarget(self, product=None, distribution=None,
                     sourcepackagename=None):
        """Set the IBugTarget in which the bug is being reported.

        :product: an IProduct
        :distribution: an IDistribution
        :sourcepackagename: an ISourcePackageName

        A product or distribution must be provided, or an AssertionError
        is raised.

        If product is specified, all other parameters must evaluate to
        False in a boolean context, or an AssertionError will be raised.

        If distribution is specified, sourcepackagename may optionally
        be provided. Product must evaluate to False in a boolean
        context, or an AssertionError will be raised.
        """
        assert product or distribution, (
            "You must specify the product or distribution in which this "
            "bug exists")

        if product:
            conflicting_context = (
                distribution or sourcepackagename)
        elif distribution:
            conflicting_context = product

        assert not conflicting_context, (
            "You must specify either an upstream context or a distribution "
            "context, but not both.")

        self.product = product
        self.distribution = distribution
        self.sourcepackagename = sourcepackagename


class BugNameField(ContentNameField):
    """Provides a a way to retrieve bugs by name."""
    errormessage = _("%s is already in use by another bug.")

    @property
    def _content_iface(self):
        """Return the `IBug` interface."""
        return IBug

    def _getByName(self, name):
        """Return a bug by name, or None."""
        try:
            return getUtility(IBugSet).getByNameOrID(name)
        except NotFoundError:
            return None


class IBugBecameQuestionEvent(Interface):
    """A bug became a question."""

    bug = Attribute("The bug that was changed into a question.")
    question = Attribute("The question that the bug became.")
    user = Attribute("The user that changed the bug into a question.")


class CreatedBugWithNoBugTasksError(Exception):
    """Raised when a bug is created with no bug tasks."""


def optional_message_subject_field():
    """A modified message subject field allowing None as a value."""
    subject_field = copy_field(IMessage['subject'])
    subject_field.required = False
    return subject_field


class IBug(IPrivacy, IHasLinkedBranches):
    """The core bug entry."""
    export_as_webservice_entry()

    id = exported(
        Int(title=_('Bug ID'), required=True, readonly=True))
    datecreated = exported(
        Datetime(title=_('Date Created'), required=True, readonly=True),
        exported_as='date_created')
    date_last_updated = exported(
        Datetime(title=_('Date Last Updated'), required=True, readonly=True))
    name = exported(
        BugNameField(
            title=_('Nickname'), required=False,
            description=_("""A short and unique name.
                Add one only if you often need to retype the URL
                but have trouble remembering the bug number."""),
            constraint=bug_name_validator))
    title = exported(
        Title(title=_('Summary'), required=True,
              description=_("""A one-line summary of the problem.""")))
    description = exported(
        Description(title=_('Description'), required=True,
             description=_("""A detailed description of the problem,
                 including the steps required to reproduce it."""),
             strip_text=True, trailing_only=True,
             min_length=1, max_length=50000))
    ownerID = Int(title=_('Owner'), required=True, readonly=True)
    owner = exported(
        Reference(IPerson, title=_("The owner's IPerson"), readonly=True))
    duplicateof = exported(
        DuplicateBug(title=_('Duplicate Of'), required=False, readonly=True),
        exported_as='duplicate_of')
    # This is redefined from IPrivacy.private because the attribute is
    # read-only. The value is guarded by setPrivate().
    private = exported(
        Bool(title=_("This bug report should be private"), required=False,
             description=_("Private bug reports are visible only to "
                           "their subscribers."),
             default=False,
             readonly=True))
    date_made_private = exported(
        Datetime(title=_('Date Made Private'), required=False, readonly=True))
    who_made_private = exported(
        PublicPersonChoice(
            title=_('Who Made Private'), required=False,
            vocabulary='ValidPersonOrTeam',
            description=_("The person who set this bug private."),
            readonly=True))
    security_related = exported(
        Bool(title=_("This bug is a security vulnerability."),
             required=False, default=False, readonly=True))
    displayname = TextLine(title=_("Text of the form 'Bug #X"),
        readonly=True)
    activity = exported(
        doNotSnapshot(CollectionField(
            title=_('Log of activity that has occurred on this bug.'),
            value_type=Reference(schema=IBugActivity),
            readonly=True)))
    initial_message = Attribute(
        "The message that was specified when creating the bug")
    bugtasks = exported(
        CollectionField(
            title=_('BugTasks on this bug, sorted upstream, then '
                    'by ubuntu, then by other distroseries.'),
            value_type=Reference(schema=IBugTask),
            readonly=True),
        exported_as='bug_tasks')
    default_bugtask = Reference(
        title=_("The first bug task to have been filed."),
        schema=IBugTask)
    affected_pillars = Attribute(
        'The "pillars", products or distributions, affected by this bug.')
    watches = exported(
        CollectionField(
            title=_("All bug watches associated with this bug."),
            value_type=Object(schema=IBugWatch),
            readonly=True),
        exported_as='bug_watches')
    cves = exported(
        CollectionField(
            title=_('CVE entries related to this bug.'),
            value_type=Reference(schema=ICve),
            readonly=True))
    has_cves = Bool(title=u"True if the bug has cve entries.")
    cve_links = Attribute('Links between this bug and CVE entries.')
    subscriptions = exported(
        doNotSnapshot(CollectionField(
            title=_('Subscriptions'),
            value_type=Reference(schema=Interface),
            readonly=True)))
    duplicates = exported(
        CollectionField(
            title=_("MultiJoin of bugs which are dupes of this one."),
            value_type=BugField(), readonly=True))
    # See lp.bugs.model.bug.Bug.attachments for why there are two similar
    # properties here.
    # attachments_unpopulated would more naturally be attachments, and
    # attachments be attachments_prepopulated, but lazr.resful cannot
    # export over a non-exported attribute in an interface.
    # https://bugs.launchpad.net/lazr.restful/+bug/625102
    attachments_unpopulated = CollectionField(
            title=_("List of bug attachments."),
            value_type=Reference(schema=IBugAttachment),
            readonly=True)
    attachments = doNotSnapshot(exported(
        CollectionField(
            title=_("List of bug attachments."),
            value_type=Reference(schema=IBugAttachment),
            readonly=True)))
    questions = Attribute("List of questions related to this bug.")
    specifications = Attribute("List of related specifications.")
    linked_branches = exported(
        CollectionField(
            title=_("Branches associated with this bug, usually "
            "branches on which this bug is being fixed."),
            value_type=Reference(schema=IBugBranch),
            readonly=True))
    tags = exported(List(
        title=_("Tags"),
        description=_("Space-separated keywords for classifying "
            "this bug report."),
            value_type=Tag(), required=False))
    is_complete = Bool(
        title=_("Is Complete?"),
        description=_(
            "True or False depending on whether this bug is considered "
            "completely addressed. A bug in Launchpad is completely "
            "addressed when there are no tasks that are still open for "
            "the bug."),
        readonly=True)
    permits_expiration = Bool(
        title=_("Does the bug's state permit expiration?"),
        description=_(
            "Expiration is permitted when the bug is not valid anywhere, "
            "a message was sent to the bug reporter, and the bug is "
            "associated with pillars that have enabled bug expiration."),
        readonly=True)
    can_expire = exported(
        Bool(
            title=_("Can the Incomplete bug expire? "
                "Expiration may happen when the bug permits expiration, "
                "and a bugtask cannot be confirmed."),
            readonly=True),
        ('devel', dict(exported=False)), exported=True)
    date_last_message = exported(
        Datetime(title=_("Date of last bug message"),
                 required=False, readonly=True))
    number_of_duplicates = exported(
        Int(title=_('The number of bugs marked as duplicates of this bug'),
            required=True, readonly=True))
    message_count = exported(
        Int(title=_('The number of comments on this bug'),
        required=True, readonly=True))
    users_affected_count = exported(
        Int(title=_('The number of users affected by this bug '
                    '(not including duplicates)'),
            required=True, readonly=True))
    users_unaffected_count = exported(
        # We don't say "(not including duplicates)" here because
        # affected and unaffected are asymmetrical that way.  If a dup
        # affects you, then the master bug affects you; but if a dup
        # *doesn't* affect you, the master bug may or may not affect
        # you, since a dup is often a specific symptom of a more
        # general master bug.
        Int(title=_('The number of users unaffected by this bug'),
            required=True, readonly=True))
    users_affected = exported(doNotSnapshot(CollectionField(
            title=_('The number of users affected by this bug '
                    '(not including duplicates)'),
            value_type=Reference(schema=IPerson),
            readonly=True)))
    users_unaffected = exported(doNotSnapshot(CollectionField(
            title=_('Users explicitly marked as unaffected '
                    '(not including duplicates)'),
            value_type=Reference(schema=IPerson),
            readonly=True)))
    users_affected_count_with_dupes = exported(
      Int(title=_('The number of users affected by this bug '
                  '(including duplicates)'),
          required=True, readonly=True))
    users_affected_with_dupes = exported(doNotSnapshot(CollectionField(
            title=_('Users affected (including duplicates)'),
            value_type=Reference(schema=IPerson),
            readonly=True)))

    heat = exported(
        Int(title=_("The 'heat' of the bug"),
        required=False, readonly=True))
    heat_last_updated = Datetime(
        title=_('Heat Last Updated'), required=False, readonly=True)

    # Adding related BugMessages provides a hook for getting at
    # BugMessage.message.visible when building bug comments.
    bug_messages = Attribute('The bug messages related to this object.')
    comment_count = Attribute(
        "The number of comments on this bug, not including the initial "
        "comment.")

    messages = doNotSnapshot(CollectionField(
            title=_("The messages related to this object, in reverse "
                    "order of creation (so newest first)."),
            readonly=True,
            value_type=Reference(schema=IMessage)))

    indexed_messages = doNotSnapshot(exported(
        CollectionField(
            title=_("The messages related to this object, in reverse "
                    "order of creation (so newest first)."),
            readonly=True,
            value_type=Reference(schema=IMessage)),
        exported_as='messages'))

    def _indexed_messages(include_content=False, include_parents=False):
        """Low level query for getting bug messages.

        :param include_content: If True retrieve the content for the messages
            too.
        :param include_parents: If True retrieve the object for parent
            messages too. If False the parent attribute will be *forced* to
            None to prevent lazy evaluation triggering database lookups.
        """

    followup_subject = Attribute("The likely subject of the next message.")

    has_patches = Attribute("Does this bug have any patches?")

    latest_patch_uploaded = exported(
        Datetime(
            title=_('Date when the most recent patch was uploaded.'),
            required=False, readonly=True))

    latest_patch = Attribute("The most recent patch of this bug.")

    official_tags = Attribute("The official bug tags relevant to this bug.")

    @accessor_for(linked_branches)
    @call_with(user=REQUEST_USER)
    @export_read_operation()
    @operation_for_version('beta')
    def getVisibleLinkedBranches(user):
        """Rertun the linked to this bug that are visible by `user`."""

    @operation_parameters(
        subject=optional_message_subject_field(),
        content=copy_field(IMessage['content']))
    @call_with(owner=REQUEST_USER)
    @export_factory_operation(IMessage, [])
    def newMessage(owner, subject, content):
        """Create a new message, and link it to this object."""

    # The level actually uses BugNotificationLevel as its vocabulary,
    # but due to circular import problems we fix that in
    # _schema_circular_imports.py rather than here.
    @operation_parameters(
        person=Reference(IPerson, title=_('Person'), required=True),
        level=Choice(
            vocabulary=DBEnumeratedType, required=False,
            title=_('Level')))
    @call_with(subscribed_by=REQUEST_USER, suppress_notify=False)
    @export_write_operation()
    def subscribe(person, subscribed_by, suppress_notify=True, level=None):
        """Subscribe `person` to the bug.

        :param person: the subscriber.
        :param subscribed_by: the person who created the subscription.
        :param suppress_notify: a flag to suppress notify call.
        :param level: The BugNotificationLevel for the new subscription.
        :return: an `IBugSubscription`.
        """

    @operation_parameters(
        person=Reference(IPerson, title=_('Person'), required=False))
    @call_with(unsubscribed_by=REQUEST_USER)
    @export_write_operation()
    def unsubscribe(person, unsubscribed_by):
        """Remove this person's subscription to this bug."""

    @operation_parameters(
        person=Reference(IPerson, title=_('Person'), required=False))
    @call_with(unsubscribed_by=REQUEST_USER)
    @export_write_operation()
    def unsubscribeFromDupes(person, unsubscribed_by):
        """Remove this person's subscription from all dupes of this bug."""

    def isSubscribed(person):
        """Is person subscribed to this bug?

        Returns True if the user is explicitly subscribed to this bug
        (no matter what the type of subscription), otherwise False.

        If person is None, the return value is always False.
        """

    def isSubscribedToDupes(person):
        """Is person directly subscribed to dupes of this bug?

        Returns True if the user is directly subscribed to at least one
        duplicate of this bug, otherwise False.
        """

    def isMuted(person):
        """Does person have a muted subscription on this bug?

        :returns: True if the user has muted all email from this bug.
        """

    @operation_parameters(
        person=Reference(IPerson, title=_('Person'), required=False))
    @call_with(muted_by=REQUEST_USER)
    @export_write_operation()
    @operation_for_version('devel')
    def mute(person, muted_by):
        """Add a muted subscription for `person`."""

    @operation_parameters(
        person=Reference(IPerson, title=_('Person'), required=False))
    @call_with(unmuted_by=REQUEST_USER)
    @export_write_operation()
    @operation_for_version('devel')
    def unmute(person, unmuted_by):
        """Remove a muted subscription for `person`.

        Returns previously muted direct subscription, if any."""

    def getDirectSubscriptions():
        """A sequence of IBugSubscriptions directly linked to this bug."""

    def getDirectSubscribers(recipients=None, level=None):
        """A list of IPersons that are directly subscribed to this bug.

        Direct subscribers have an entry in the BugSubscription table.
        """

    def getDirectSubscribersWithDetails():
        """Get direct subscribers and their subscriptions for the bug.

        Those with muted bug subscriptions are excluded from results.

        :returns: A ResultSet of tuples (Person, BugSubscription)
            representing a subscriber and their bug subscription.
        """

    def getIndirectSubscribers(recipients=None, level=None):
        """Return IPersons that are indirectly subscribed to this bug.

        Indirect subscribers get bugmail, but don't have an entry in the
        BugSubscription table. This includes bug contacts, subscribers from
        dupes, etc.
        """

    def getAlsoNotifiedSubscribers(recipients=None, level=None):
        """Return IPersons in the "Also notified" subscriber list.

        This includes bug contacts and assignees, but not subscribers
        from duplicates.
        """

    def getSubscriptionsFromDuplicates():
        """Return IBugSubscriptions subscribed from dupes of this bug."""

    def getSubscribersFromDuplicates():
        """Return IPersons subscribed from dupes of this bug."""

    def getSubscribersForPerson(person):
        """Find the persons or teams by which person is subscribed.

        This call should be quite cheap to make and performs a single query.

        :return: An IResultSet.
        """

    def getSubscriptionForPerson(person):
        """Return the `BugSubscription` for a `Person` to this `Bug`.

        If no such `BugSubscription` exists, return None.
        """

    def getSubscriptionInfo(level):
        """Return a `BugSubscriptionInfo` at the given `level`.

        :param level: A member of `BugNotificationLevel`.
        """

    def getBugNotificationRecipients(duplicateof=None, old_bug=None,
                                     include_master_dupe_subscribers=False):
        """Return a complete INotificationRecipientSet instance.

        The INotificationRecipientSet instance will contain details of
        all recipients for bug notifications sent by this bug; this
        includes email addresses and textual and header-ready
        rationales. See
        canonical.launchpad.interfaces.BugNotificationRecipients for
        details of this implementation.
        If this bug is a dupe, set include_master_dupe_subscribers to
        True to include the master bug's subscribers as recipients.
        """

    def addCommentNotification(message, recipients=None, activity=None):
        """Add a bug comment notification.

        If a BugActivity instance is provided as an `activity`, it is linked
        to the notification."""

    def addChange(change, recipients=None):
        """Record a change to the bug.

        :param change: An `IBugChange` instance from which to take the
            change data.
        :param recipients: A set of `IBugNotificationRecipient`s to whom
            to send notifications about this change. If None is passed
            the default list of recipients for the bug will be used.
        """

    def expireNotifications():
        """Expire any pending notifications that have not been emailed.

        This will mark any notifications related to this bug as having
        been emailed.  The intent is to prevent large quantities of
        bug mail being generated during bulk imports or changes.
        """

    @call_with(owner=REQUEST_USER)
    @rename_parameters_as(
        bugtracker='bug_tracker', remotebug='remote_bug')
    @export_factory_operation(
        IBugWatch, ['bugtracker', 'remotebug'])
    def addWatch(bugtracker, remotebug, owner):
        """Create a new watch for this bug on the given remote bug and bug
        tracker, owned by the person given as the owner.
        """

    def removeWatch(bug_watch, owner):
        """Remove a bug watch from the bug."""

    @call_with(owner=REQUEST_USER)
    @operation_parameters(target=copy_field(IBugTask['target']))
    @export_factory_operation(IBugTask, [])
    def addTask(owner, target):
        """Create a new bug task on this bug."""

    def hasBranch(branch):
        """Is this branch linked to this bug?"""

    @call_with(owner=REQUEST_USER)
    @operation_parameters(
        data=Bytes(constraint=attachment_size_constraint),
        comment=Text(), filename=TextLine(), is_patch=Bool(),
        content_type=TextLine(), description=Text())
    @export_factory_operation(IBugAttachment, [])
    def addAttachment(owner, data, comment, filename, is_patch=False,
                      content_type=None, description=None):
        """Attach a file to this bug.

        :owner: An IPerson.
        :data: A file-like object, or a `str`.
        :description: A brief description of the attachment.
        :comment: An IMessage or string.
        :filename: A string.
        :is_patch: A boolean.
        """

    def linkAttachment(owner, file_alias, comment, is_patch=False,
                       description=None):
        """Link an `ILibraryFileAlias` to this bug.

        :owner: An IPerson.
        :file_alias: The `ILibraryFileAlias` to link to this bug.
        :description: A brief description of the attachment.
        :comment: An IMessage or string.
        :is_patch: A boolean.

        This method should only be called by addAttachment() and
        FileBugViewBase.submit_bug_action, otherwise
        we may get inconsistent settings of bug.private and
        file_alias.restricted.
        """

    def linkCVE(cve, user):
        """Ensure that this CVE is linked to this bug."""

    # XXX intellectronica 2008-11-06 Bug #294858:
    # We use this method to suppress the return value
    # from linkCVE, which we don't want to export.
    # In the future we'll have a decorator which does that for us.
    @call_with(user=REQUEST_USER)
    @operation_parameters(cve=Reference(ICve, title=_('CVE'), required=True))
    @export_operation_as('linkCVE')
    @export_write_operation()
    def linkCVEAndReturnNothing(cve, user):
        """Ensure that this CVE is linked to this bug."""

    @call_with(user=REQUEST_USER)
    @operation_parameters(cve=Reference(ICve, title=_('CVE'), required=True))
    @export_write_operation()
    def unlinkCVE(cve, user):
        """Ensure that any links between this bug and the given CVE are
        removed.
        """

    def findCvesInText(text, user):
        """Find any CVE references in the given text, make sure they exist
        in the database, and are linked to this bug.

        The user is the one linking to the CVE.
        """

    def canBeAQuestion():
        """Return True of False if a question can be created from this bug.

        A Question can be created from a bug if:
        1. There is only one bugtask with a status of New, Incomplete,
           Confirmed, or Wont Fix. Any other bugtasks must be Invalid.
        2. The bugtask's target uses Launchpad to track bugs.
        3. The bug was not made into a question previously.
        """

    def convertToQuestion(person, comment=None):
        """Create and return a Question from this Bug.

        Bugs that are also in external bug trackers cannot be converted
        to questions. This is also true for bugs that are being developed.

        The `IQuestionTarget` is provided by the `IBugTask` that is not
        Invalid and is not a conjoined slave. Only one question can be
        made from a bug.

        An AssertionError is raised if the bug has zero or many BugTasks
        that can provide a QuestionTarget. It will also be raised if a
        question was previously created from the bug.

        :person: The `IPerson` creating a question from this bug
        :comment: A string. An explanation of why the bug is a question.
        """

    def getQuestionCreatedFromBug():
        """Return the question created from this Bug, or None."""

    def linkMessage(message, bugwatch=None, user=None,
                    remote_comment_id=None):
        """Add a comment to this bug.

            :param message: The `IMessage` to be used as a comment.
            :param bugwatch: The `IBugWatch` of the bug this comment was
                imported from, if it's an imported comment.
            :param user: The `IPerson` adding the comment.
            :param remote_comment_id: The id this comment has in the
                remote bug tracker, if it's an imported comment.
        """

    def getMessagesForView(slice_info):
        """Return BugMessage,Message,MessageChunks for renderinger.

        This eager loads message.owner validity associated with the
        bugmessages.

        :param slice_info: Either None or a list of slices to constraint the
            returned rows. The step parameter in each slice is ignored.
        """

    @operation_parameters(
        target=Reference(schema=Interface, title=_('Target')))
    @call_with(owner=REQUEST_USER)
    @export_factory_operation(Interface, [])
    def addNomination(owner, target):
        """Nominate a bug for an IDistroSeries or IProductSeries.

        :owner: An IPerson.
        :target: An IDistroSeries or IProductSeries.

        This method creates and returns a BugNomination. (See
        lp.bugs.model.bugnomination.BugNomination.)
        """

    @operation_parameters(
        target=Reference(schema=Interface, title=_('Target')))
    @export_read_operation()
    def canBeNominatedFor(target):
        """Can this bug nominated for this target?

        :nomination_target: An IDistroSeries or IProductSeries.

        Returns True or False.
        """

    @operation_parameters(
        target=Reference(schema=Interface, title=_('Target')))
    @operation_returns_entry(Interface)
    @export_read_operation()
    def getNominationFor(target):
        """Return the IBugNomination for the target.

        If no nomination is found, a NotFoundError is raised.

        :param nomination_target: An IDistroSeries or IProductSeries.
        """

    @operation_parameters(
        target=Reference(
            schema=Interface, title=_('Target'), required=False),
        nominations=List(
            title=_("Nominations to search through."),
            value_type=Reference(schema=Interface),  # IBugNomination
            required=False))
    @operation_returns_collection_of(Interface)  # IBugNomination
    @export_read_operation()
    def getNominations(target=None, nominations=None):
        """Return a list of all IBugNominations for this bug.

        The list is ordered by IBugNominations.target.bugtargetdisplayname.

        :param target: An IProduct or IDistribution. Only nominations
            for this target are returned.
        :param nominations: The list of nominations to search through.
            If none is given, the bug's nominations are looked through.
            This can be useful when having to call this method multiple
            times, to avoid getting the list of nominations each time.
        """

    def getBugWatch(bugtracker, remote_bug):
        """Return the BugWatch that has the given bugtracker and remote bug.

        Return None if this bug doesn't have such a bug watch.
        """

    def setStatus(target, status, user):
        """Set the status of the bugtask related to the specified target.

            :target: The target of the bugtask that should be modified.
            :status: The status the bugtask should be set to.
            :user: The `IPerson` doing the change.

        If a bug task was edited, emit a
        `lazr.lifecycle.interfaces.IObjectModifiedEvent` and
        return the edited bugtask.

        Return None if no bugtask was edited.
        """

    @mutator_for(private)
    @operation_parameters(private=copy_field(private))
    @call_with(who=REQUEST_USER)
    @export_write_operation()
    def setPrivate(private, who):
        """Set bug privacy.

            :private: True/False.
            :who: The IPerson who is making the change.

        Return True if a change is made, False otherwise.
        """

    @mutator_for(security_related)
    @operation_parameters(security_related=copy_field(security_related))
    @call_with(who=REQUEST_USER)
    @export_write_operation()
    def setSecurityRelated(security_related, who):
        """Set bug security.

            :security_related: True/False.
            :who: The IPerson who is making the change.

        This may also cause the security contact to be subscribed
        if one is registered and if the bug is not private.

        Return True if a change is made, False otherwise.
        """

    @operation_parameters(
        private=copy_field(private),
        security_related=copy_field(security_related),
        )
    @call_with(who=REQUEST_USER)
    @export_write_operation()
    @operation_for_version("devel")
    def setPrivacyAndSecurityRelated(private, security_related, who):
        """Set bug privacy and security .

            :private: True/False.
            :security_related: True/False.
            :who: The IPerson who is making the change.

        Return (private_changed, security_related_changed) tuple.
        """

    def getBugTask(target):
        """Return the bugtask with the specified target.

        Return None if no such bugtask is found.
        """

    def getBugTasksByPackageName(bugtasks):
        """Return a mapping from `ISourcePackageName` to its bug tasks.

        This mapping is suitable to pass as the bugtasks_by_package
        cache to getConjoinedMaster().

        The mapping is from a `ISourcePackageName` to all the bug tasks
        that are targeted to such a package name, no matter which
        distribution or distro series it is.

        All the tasks that don't have a package will be available under
        None.
        """

    @call_with(user=REQUEST_USER)
    @export_write_operation()
    def isUserAffected(user):
        """Is :user: marked as affected by this bug?"""

    @operation_parameters(
        affected=Bool(
            title=_("Does this bug affect you?"),
            required=False, default=True))
    @call_with(user=REQUEST_USER)
    @export_write_operation()
    def markUserAffected(user, affected=True):
        """Mark :user: as affected by this bug."""

    @mutator_for(duplicateof)
    @operation_parameters(duplicate_of=copy_field(duplicateof))
    @export_write_operation()
    def markAsDuplicate(duplicate_of):
        """Mark this bug as a duplicate of another."""

    @operation_parameters(
        comment_number=Int(
            title=_('The number of the comment in the list of messages.'),
            required=True),
        visible=Bool(title=_('Show this comment?'), required=True))
    @call_with(user=REQUEST_USER)
    @export_write_operation()
    def setCommentVisibility(user, comment_number, visible):
        """Set the visible attribute on a bug comment.  This is restricted
        to Launchpad admins, and will return a HTTP Error 401: Unauthorized
        error for non-admin callers.
        """

    def userCanView(user):
        """Return True if `user` can see this IBug, false otherwise."""

    @operation_parameters(
        submission=Reference(
            Interface, title=_('A HWDB submission'), required=True))
    @export_write_operation()
    def linkHWSubmission(submission):
        """Link a `HWSubmission` to this bug."""

    @operation_parameters(
        submission=Reference(
            Interface, title=_('A HWDB submission'), required=True))
    @export_write_operation()
    def unlinkHWSubmission(submission):
        """Remove a link to a `HWSubmission`."""

    @call_with(user=REQUEST_USER)
    @operation_returns_collection_of(Interface)
    @export_read_operation()
    def getHWSubmissions(user=None):
        """Return HWDB submissions linked to this bug.

        :return: A sequence of HWDB submissions linked to this bug.
        :param user: The user making the request.

        Only those submissions are returned which the user can access.
        Public submissions are always included; private submisisons only
        if the user is the owner or an admin.
        """

    def setHeat(heat, timestamp=None, affected_targets=None):
        """Set the heat for the bug."""

    def updateHeat(affected_targets=None):
        """Update the heat for the bug."""

    @operation_parameters(
        days_old=Int(
            title=_('Number of days of inactivity for which to check.'),
            required=False))
    @export_read_operation()
    def isExpirable(days_old=None):
        """Is this bug eligible for expiration and was it last updated
        more than X days ago?

        If days_old is None the default number of days without activity
        is used.

        Returns True or False.
        """

    def getActivityForDateRange(start_date, end_date):
        """Return all the `IBugActivity` for this bug in a date range.

        :param start_date: The earliest date for which activity can be
            returned.
        :param end_date: The latest date for which activity can be
            returned.
        """


# We are forced to define these now to avoid circular import problems.
IBugAttachment['bug'].schema = IBug
IBugWatch['bug'].schema = IBug
IMessage['bugs'].value_type.schema = IBug
ICve['bugs'].value_type.schema = IBug

# In order to avoid circular dependencies, we only import
# IBugSubscription (which itself imports IBug) here, and assign it as
# the value type for the `subscriptions` collection.
from lp.bugs.interfaces.bugsubscription import IBugSubscription
IBug['subscriptions'].value_type.schema = IBugSubscription


class IBugDelta(Interface):
    """The quantitative change made to a bug that was edited."""

    bug = Attribute("The IBug, after it's been edited.")
    bug_before_modification = Attribute("The IBug, before it's been edited.")
    bugurl = Attribute("The absolute URL to the bug.")
    user = Attribute("The IPerson that did the editing.")

    # fields on the bug itself
    title = Attribute("A dict with two keys, 'old' and 'new', or None.")
    description = Attribute("A dict with two keys, 'old' and 'new', or None.")
    private = Attribute("A dict with two keys, 'old' and 'new', or None.")
    security_related = Attribute(
        "A dict with two keys, 'old' and 'new', or None.")
    name = Attribute("A dict with two keys, 'old' and 'new', or None.")
    duplicateof = Attribute(
        "A dict with two keys, 'old' and 'new', or None. Key values are "
        "IBug's")

    # other things linked to the bug
    bugwatch = Attribute(
        "A dict with two keys, 'old' and 'new', or None. Key values are "
        "IBugWatch's.")
    attachment = Attribute(
        "A dict with two keys, 'old' and 'new', or None. Key values are "
        "IBugAttachment's.")
    cve = Attribute(
        "A dict with two keys, 'old' and 'new', or None. Key values are "
        "ICve's")
    added_bugtasks = Attribute(
        "A list or tuple of IBugTasks, one IBugTask, or None.")
    bugtask_deltas = Attribute(
        "A sequence of IBugTaskDeltas, one IBugTaskDelta or None.")


# A simple vocabulary for the subscribe_to_existing_bug form field.
SUBSCRIBE_TO_BUG_VOCABULARY = SimpleVocabulary.fromItems(
    [('yes', True), ('no', False)])


class IBugAddForm(IBug):
    """Information we need to create a bug"""
    id = Int(title=_("Bug #"), required=False)
    product = Choice(
            title=_("Project"), required=False,
            description=_("""The thing you found this bug in,
            which was installed by something other than apt-get, rpm,
            emerge or similar"""),
            vocabulary="Product")
    packagename = Choice(
            title=_("Package Name"), required=False,
            description=_("""The package you found this bug in,
            which was installed via apt-get, rpm, emerge or similar."""),
            vocabulary="BinaryAndSourcePackageName")
    title = Title(title=_('Summary'), required=True)
    distribution = Choice(
            title=_("Linux Distribution"), required=True,
            description=_(
                "Ubuntu, Debian, Gentoo, etc. You can file bugs only on "
                "distrubutions using Launchpad as their primary bug "
                "tracker."),
            vocabulary="DistributionUsingMalone")
    owner = Int(title=_("Owner"), required=True)
    comment = Description(
        title=_('Further information'),
        strip_text=True, trailing_only=True,
        min_length=1, max_length=50000, required=False)
    bug_already_reported_as = Choice(
        title=_("This bug has already been reported as ..."), required=False,
        vocabulary="Bug")
    filecontent = Bytes(
        title=u"Attachment", required=False,
        constraint=attachment_size_constraint)
    patch = Bool(title=u"This attachment is a patch", required=False,
        default=False)
    attachment_description = Title(title=u'Description', required=False)
    status = Choice(
        title=_('Status'),
        values=list(
            item for item in BugTaskStatus.items.items
            if item != BugTaskStatus.UNKNOWN),
        default=IBugTask['status'].default)
    importance = Choice(
        title=_('Importance'),
        values=list(
            item for item in BugTaskImportance.items.items
            if item != BugTaskImportance.UNKNOWN),
        default=IBugTask['importance'].default)
    milestone = Choice(
        title=_('Milestone'), required=False,
        vocabulary='Milestone')
    assignee = PublicPersonChoice(
        title=_('Assign to'), required=False,
        vocabulary='ValidAssignee')
    subscribe_to_existing_bug = Choice(
        title=u'Subscribe to this bug',
        vocabulary=SUBSCRIBE_TO_BUG_VOCABULARY,
        required=True, default=False)


class IProjectGroupBugAddForm(IBugAddForm):
    """Create a bug for an IProjectGroup."""
    product = Choice(
        title=_("Project"), required=True,
        vocabulary="ProjectProductsUsingMalone")


class IFrontPageBugAddForm(IBugAddForm):
    """Create a bug for any bug target."""

    bugtarget = Reference(
        schema=Interface, title=_("Where did you find the bug?"),
        required=True)


class IBugSet(Interface):
    """A set of bugs."""

    def get(bugid):
        """Get a specific bug by its ID.

        If it can't be found, NotFoundError will be raised.
        """

    def getByNameOrID(bugid):
        """Get a specific bug by its ID or nickname

        If it can't be found, NotFoundError will be raised.
        """

    def searchAsUser(user, duplicateof=None, orderBy=None, limit=None):
        """Find bugs matching the search criteria provided.

        To search as an anonymous user, the user argument passed
        should be None.
        """

    def queryByRemoteBug(bugtracker, remotebug):
        """Find one or None bugs for the BugWatch and bug tracker.

        Find one or None bugs in Launchpad that have a BugWatch matching
        the given bug tracker and remote bug id.
        """

    def createBug(bug_params, notify_event=True):
        """Create a bug and return it.

        :param bug_params: A CreateBugParams object.
        :param notify_event: notify subscribers of the bug creation event.
        :return: the new bug, or a tuple of bug, event when notify_event
            is false.

        Things to note when using this factory:

          * if no description is passed, the comment will be used as the
            description

          * the reporter will be subscribed to the bug

          * distribution, product and package contacts (whichever ones are
            applicable based on the bug report target) will be subscribed to
            all *public bugs only*

          * for public upstream bugs where there is no upstream bug contact,
            the product owner will be subscribed instead

          * if either product or distribution is specified, an appropiate
            bug task will be created
        """

    def createBugWithoutTarget(bug_params):
        """Create a bug without a bug target and return it.

        This is a variant of `createBug()` that does not create the
        first bugtask for the bug. The bug creation event is not sent,
        and a `(bug, event)` tuple is returned instead. The caller is
        therefore responsible for sending the event at a later point.

        See `createBug()` for more information.
        """

    def getDistinctBugsForBugTasks(bug_tasks, user, limit=10):
        """Return :limit: distinct Bugs for a given set of BugTasks.

        :param bug_tasks: An iterable of IBugTasks for which we should
            return Bugs.
        :param user: The Person getting the list of Bugs. Only Bugs
            visible to :user: will be returned.
        :param limit: The number of distinct Bugs to return.
        """

    def getByNumbers(bug_numbers):
        """Get `IBug` instances identified by the `bug_numbers` iterable.

        :param bug_numbers: An iterable of bug numbers for which we should
            return Bugs.
        """

    def personIsDirectSubscriber(person):
        """Return True if the person is a direct subscriber to this `IBug`.

        Otherwise, return False.
        """

    def personIsAlsoNotifiedSubscriber(person):
        """Return True if the person is an indirect subscriber to this `IBug`.

        Otherwise, return False.
        """

    def personIsSubscribedToDuplicate(person):
        """Return True if the person subscribed to a duplicate of this `IBug`.

        Otherwise, return False.
        """

    def dangerousGetAllBugs():
        # XXX 2010-01-08 gmb bug=505850:
        #     Note, this method should go away when we have a proper
        #     permissions system for scripts.
        """DO NOT CALL THIS METHOD.

        This method exists solely to allow the bug heat script to grab
        all the bugs in the database - including private ones - and
        iterate over them. DO NOT USE IT UNLESS YOU KNOW WHAT YOU'RE
        DOING. AND IF YOU KNOW WHAT YOU'RE DOING YOU KNOW BETTER THAN TO
        USE THIS ANYWAY.
        """

    def getBugsWithOutdatedHeat(max_heat_age):
        """Return the set of bugs whose heat is out of date.

        :param max_heat_age: The maximum age, in days, that a bug's heat
                             can be before it is included in the
                             returned set.
        """


class IFileBugData(Interface):
    """A class containing extra data to be used when filing a bug."""

    initial_summary = Attribute("The initial summary for the bug.")
    private = Attribute("Whether the bug should be private.")
    extra_description = Attribute("A longer description of the bug.")
    initial_tags = Attribute("The initial tags for the bug.")
    subscribers = Attribute("The initial subscribers for the bug.")
    comments = Attribute("Comments to add to the bug.")
    attachments = Attribute("Attachments to add to the bug.")
    hwdb_submission_keys = Attribute("HWDB submission keys for the bug.")


class IBugMute(Interface):
    """A mute on an IBug."""

    person = PersonChoice(
        title=_('Person'), required=True, vocabulary='ValidPersonOrTeam',
        readonly=True, description=_("The person subscribed."))
    bug = Reference(
        IBug, title=_("Bug"),
        required=True, readonly=True,
        description=_("The bug to be muted."))
    date_created = Datetime(
        title=_("The date on which the mute was created."), required=False,
        readonly=True)
