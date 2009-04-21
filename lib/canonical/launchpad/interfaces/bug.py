# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces related to bugs."""

__metaclass__ = type

__all__ = [
    'CreateBugParams',
    'CreatedBugWithNoBugTasksError',
    'IBug',
    'IBugAddForm',
    'IBugBecameQuestionEvent',
    'IBugDelta',
    'IBugSet',
    'IFrontPageBugAddForm',
    'IProjectBugAddForm',
    'InvalidBugTargetType',
    'InvalidDuplicateValue',
    'UserCannotSetCommentVisibility',
    ]

from zope.component import getUtility
from zope.interface import Interface, Attribute
from zope.schema import (
    Bool, Bytes, Choice, Datetime, Int, List, Object, Text, TextLine)

from canonical.launchpad import _
from canonical.launchpad.fields import (
    BugField, ContentNameField, DuplicateBug, PublicPersonChoice, Tag, Title)
from canonical.launchpad.interfaces.bugattachment import IBugAttachment
from canonical.launchpad.interfaces.bugtarget import IBugTarget
from canonical.launchpad.interfaces.bugtask import IBugTask
from canonical.launchpad.interfaces.bugwatch import IBugWatch
from canonical.launchpad.interfaces.cve import ICve
from canonical.launchpad.interfaces.launchpad import NotFoundError
from canonical.launchpad.interfaces.message import IMessage
from lp.registry.interfaces.mentoringoffer import ICanBeMentored
from lp.registry.interfaces.person import IPerson
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.validators.bugattachment import (
    bug_attachment_size_constraint)

from lazr.restful.declarations import (
    REQUEST_USER, call_with, export_as_webservice_entry,
    export_factory_operation, export_operation_as, export_write_operation,
    exported, mutator_for, operation_parameters, rename_parameters_as,
    webservice_error)
from lazr.restful.fields import CollectionField, Reference
from lazr.restful.interface import copy_field


class CreateBugParams:
    """The parameters used to create a bug."""

    def __init__(self, owner, title, comment=None, description=None, msg=None,
                 status=None, assignee=None, datecreated=None,
                 security_related=False, private=False, subscribers=(),
                 binarypackagename=None, tags=None, subscribe_reporter=True):
        self.owner = owner
        self.title = title
        self.comment = comment
        self.description = description
        self.msg = msg
        self.status = status
        self.assignee = assignee
        self.datecreated = datecreated
        self.security_related = security_related
        self.private = private
        self.subscribers = subscribers

        self.product = None
        self.distribution = None
        self.sourcepackagename = None
        self.binarypackagename = binarypackagename
        self.tags = tags
        self.subscribe_reporter = subscribe_reporter

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
        be provided. product must evaluate to False in a boolean
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


class IBug(ICanBeMentored):
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
            constraint=name_validator))
    title = exported(
        Title(title=_('Summary'), required=True,
              description=_("""A one-line summary of the problem.""")))
    description = exported(
        Text(title=_('Description'), required=True,
             description=_("""A detailed description of the problem,
                 including the steps required to reproduce it."""),
             max_length=50000))
    ownerID = Int(title=_('Owner'), required=True, readonly=True)
    owner = exported(
        Reference(IPerson, title=_("The owner's IPerson"), readonly=True))
    duplicateof = DuplicateBug(title=_('Duplicate Of'), required=False)
    readonly_duplicateof = exported(
        DuplicateBug(title=_('Duplicate Of'), required=False, readonly=True),
        exported_as='duplicate_of')
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
        Bool(title=_("This bug is a security vulnerability"),
             required=False, default=False))
    displayname = TextLine(title=_("Text of the form 'Bug #X"),
        readonly=True)
    activity = Attribute('SQLObject.Multijoin of IBugActivity')
    initial_message = Attribute(
        "The message that was specified when creating the bug")
    bugtasks = exported(
        CollectionField(
            title=_('BugTasks on this bug, sorted upstream, then '
                    'ubuntu, then other distroseriess.'),
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
    cve_links = Attribute('Links between this bug and CVE entries.')
    subscriptions = exported(
        CollectionField(
            title=_('Subscriptions.'),
            value_type=Reference(schema=Interface),
            readonly=True))
    duplicates = exported(
        CollectionField(
            title=_('MultiJoin of the bugs which are dups of this one'),
            value_type=BugField(), readonly=True))
    attachments = exported(
        CollectionField(
            title=_("List of bug attachments."),
            value_type=Reference(schema=IBugAttachment),
            readonly=True))
    questions = Attribute("List of questions related to this bug.")
    specifications = Attribute("List of related specifications.")
    bug_branches = Attribute(
        "Branches associated with this bug, usually "
        "branches on which this bug is being fixed.")
    tags = exported(
        List(title=_("Tags"), description=_("Separated by whitespace."),
             value_type=Tag(), required=False))
    is_complete = Bool(
        description=_(
            "True or False depending on whether this bug is considered "
            "completely addressed. A bug is Launchpad is completely "
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
    can_expire = Bool(
        title=_("Can the Incomplete bug expire if it becomes inactive? "
                "Expiration may happen when the bug permits expiration, "
                "and a bugtask cannot be confirmed."),
        readonly=True)
    date_last_message = exported(
        Datetime(title=_('Date of last bug message'),
                 required=False, readonly=True))
    number_of_duplicates = Int(
        title=_('The number of bugs marked as duplicates of this bug'),
        required=True, readonly=True)
    message_count = Int(
        title=_('The number of comments on this bug'),
        required=True, readonly=True)
    users_affected_count = exported(
        Int(title=_('The number of users affected by this bug'),
            required=True, readonly=True))
    users_unaffected_count = exported(
        Int(title=_('The number of users unaffected by this bug'),
            required=True, readonly=True))
    users_affected = exported(CollectionField(
            title=_('Users affected'),
            value_type=Reference(schema=IPerson),
            readonly=True))

    # Adding related BugMessages provides a hook for getting at
    # BugMessage.visible when building bug comments.
    bug_messages = Attribute('The bug messages related to this object.')

    messages = CollectionField(
            title=_("The messages related to this object, in reverse "
                    "order of creation (so newest first)."),
            readonly=True,
            value_type=Reference(schema=IMessage))

    indexed_messages = exported(
        CollectionField(
            title=_("The messages related to this object, in reverse "
                    "order of creation (so newest first)."),
            readonly=True,
            value_type=Reference(schema=IMessage)),
        exported_as='messages')

    followup_subject = Attribute("The likely subject of the next message.")

    @operation_parameters(
        subject=copy_field(IMessage['subject']),
        content=copy_field(IMessage['content']))
    @call_with(owner=REQUEST_USER)
    @export_factory_operation(IMessage, [])
    def newMessage(owner, subject, content):
        """Create a new message, and link it to this object."""

    # subscription-related methods

    @operation_parameters(
        person=Reference(IPerson, title=_('Person'), required=True))
    @call_with(subscribed_by=REQUEST_USER)
    @export_write_operation()
    def subscribe(person, subscribed_by):
        """Subscribe `person` to the bug.

        :param person: the subscriber.
        :param subscribed_by: the person who created the subscription.
        :return: an `IBugSubscription`.
        """

    @call_with(person=REQUEST_USER, unsubscribed_by=REQUEST_USER)
    @export_write_operation()
    def unsubscribe(person, unsubscribed_by):
        """Remove this person's subscription to this bug."""

    def unsubscribeFromDupes(person):
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

    def getDirectSubscriptions():
        """A sequence of IBugSubscriptions directly linked to this bug."""

    def getDirectSubscribers():
        """A list of IPersons that are directly subscribed to this bug.

        Direct subscribers have an entry in the BugSubscription table.
        """

    def getIndirectSubscribers():
        """Return IPersons that are indirectly subscribed to this bug.

        Indirect subscribers get bugmail, but don't have an entry in the
        BugSubscription table. This includes bug contacts, subscribers from
        dupes, etc.
        """

    def getAlsoNotifiedSubscribers():
        """Return IPersons in the "Also notified" subscriber list.

        This includes bug contacts and assignees, but not subscribers
        from duplicates.
        """

    def getSubscriptionsFromDuplicates():
        """Return IBugSubscriptions subscribed from dupes of this bug."""

    def getSubscribersFromDuplicates():
        """Return IPersons subscribed from dupes of this bug."""

    def getBugNotificationRecipients(duplicateof=None, old_bug=None):
        """Return a complete INotificationRecipientSet instance.

        The INotificationRecipientSet instance will contain details of
        all recipients for bug notifications sent by this bug; this
        includes email addresses and textual and header-ready
        rationales. See
        canonical.launchpad.interfaces.BugNotificationRecipients for
        details of this implementation.
        """

    def addChangeNotification(text, person, recipients=None, when=None):
        """Add a bug change notification."""

    def addCommentNotification(message, recipients=None):
        """Add a bug comment notification."""

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

    def addBranch(branch, registrant, whiteboard=None, status=None):
        """Associate a branch with this bug.

        :param branch: The branch being linked to the bug
        :param registrant: The user making the link.
        :param whiteboard: A space where people can write about the bug fix
        :param status: The status of the fix in the branch

        Returns an IBugBranch.
        """

    def removeBranch(branch, user):
        """Unlink a branch from this bug.

        :param branch: The branch being unlinked from the bug
        :param registrant: The user unlinking the branch
        """

    @call_with(owner=REQUEST_USER)
    @operation_parameters(
        data=Bytes(constraint=bug_attachment_size_constraint),
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

    def getMessageChunks():
        """Return MessageChunks corresponding to comments made on this bug"""

    def getNullBugTask(product=None, productseries=None,
                    sourcepackagename=None, distribution=None,
                    distroseries=None):
        """Create an INullBugTask and return it for the given parameters."""

    def addNomination(owner, target):
        """Nominate a bug for an IDistroSeries or IProductSeries.

        :owner: An IPerson.
        :target: An IDistroSeries or IProductSeries.

        The nomination will be automatically approved, if the user has
        permission to approve it.

        This method creates and returns a BugNomination. (See
        canonical.launchpad.database.bugnomination.BugNomination.)
        """

    def canBeNominatedFor(nomination_target):
        """Can this bug nominated for this target?

        :nomination_target: An IDistroSeries or IProductSeries.

        Returns True or False.
        """

    def getNominationFor(nomination_target):
        """Return the IBugNomination for the target.

        If no nomination is found, a NotFoundError is raised.

        :param nomination_target: An IDistroSeries or IProductSeries.
        """

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

    @mutator_for(readonly_duplicateof)
    @operation_parameters(duplicate_of=copy_field(readonly_duplicateof))
    @export_write_operation()
    def markAsDuplicate(duplicate_of):
        """Mark this bug as a duplicate of another."""

    @operation_parameters(
        comment_number=Int(
            title=_('The number of the comment in the list of messages.'),
            required=True),
        visible=Bool(title=_('Hide this comment?'), required=True))
    @call_with(user=REQUEST_USER)
    @export_write_operation()
    def setCommentVisibility(user, comment_number, visible):
        """Set the visible attribute on a bug comment."""


class InvalidDuplicateValue(Exception):
    """A bug cannot be set as the duplicate of another."""
    webservice_error(417)


class UserCannotSetCommentVisibility(Exception):
    """Bug comment visibility can only be set by admins."""
    webservice_error(401)



# We are forced to define these now to avoid circular import problems.
IBugAttachment['bug'].schema = IBug
IBugWatch['bug'].schema = IBug
IMessage['bugs'].value_type.schema = IBug

# In order to avoid circular dependencies, we only import
# IBugSubscription (which itself imports IBug) here, and assign it as
# the value type for the `subscriptions` collection.
from canonical.launchpad.interfaces.bugsubscription import IBugSubscription
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
    comment = Text(
        title=_('Further information'),
        required=False)
    bug_already_reported_as = Choice(
        title=_("This bug has already been reported as ..."), required=False,
        vocabulary="Bug")
    filecontent = Bytes(
        title=u"Attachment", required=False,
        constraint=bug_attachment_size_constraint)
    patch = Bool(title=u"This attachment is a patch", required=False,
        default=False)
    attachment_description = Title(title=u'Description', required=False)


class IProjectBugAddForm(IBugAddForm):
    """Create a bug for an IProject."""
    product = Choice(
        title=_("Project"), required=True,
        vocabulary="ProjectProductsUsingMalone")


class IFrontPageBugAddForm(IBugAddForm):
    """Create a bug for any bug target."""

    bugtarget = Reference(
        schema=IBugTarget, title=_("Where did you find the bug?"),
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

    def createBug(bug_params):
        """Create a bug and return it.

        :bug_params: A CreateBugParams object.

        Things to note when using this factory:

          * if no description is passed, the comment will be used as the
            description

          * the reporter will be subscribed to the bug

          * distribution, product and package contacts (whichever ones are
            applicable based on the bug report target) will bug subscribed to
            all *public bugs only*

          * for public upstreams bugs where there is no upstream bug contact,
            the product owner will be subscribed instead

          * if either product or distribution is specified, an appropiate
            bug task will be created

          * binarypackagename, if not None, will be added to the bug's
            description
        """

class InvalidBugTargetType(Exception):
    """Bug target's type is not valid."""
    webservice_error(400)
