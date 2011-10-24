# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213,E0602

"""Bug task interfaces."""

__metaclass__ = type

__all__ = [
    'BUG_SUPERVISOR_BUGTASK_STATUSES',
    'BugBlueprintSearch',
    'BugBranchSearch',
    'BugTagsSearchCombinator',
    'BugTaskImportance',
    'BugTaskSearchParams',
    'BugTaskStatus',
    'BugTaskStatusSearch',
    'BugTaskStatusSearchDisplay',
    'CannotDeleteBugtask',
    'DB_INCOMPLETE_BUGTASK_STATUSES',
    'DB_UNRESOLVED_BUGTASK_STATUSES',
    'DEFAULT_SEARCH_BUGTASK_STATUSES_FOR_DISPLAY',
    'get_bugtask_status',
    'IAddBugTaskForm',
    'IAddBugTaskWithProductCreationForm',
    'IBugTask',
    'IBugTaskDelete',
    'IBugTaskDelta',
    'IBugTaskSearch',
    'IBugTaskSet',
    'ICreateQuestionFromBugTaskForm',
    'IFrontPageBugTaskSearch',
    'IllegalRelatedBugTasksParams',
    'IllegalTarget',
    'INominationsReviewTableBatchNavigator',
    'IPersonBugTaskSearch',
    'IRemoveQuestionFromBugTaskForm',
    'IUpstreamProductBugTaskSearch',
    'normalize_bugtask_status',
    'RESOLVED_BUGTASK_STATUSES',
    'UNRESOLVED_BUGTASK_STATUSES',
    'UserCannotEditBugTaskAssignee',
    'UserCannotEditBugTaskImportance',
    'UserCannotEditBugTaskMilestone',
    'UserCannotEditBugTaskStatus',
    'valid_remote_bug_url',
    ]

import httplib

from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    EnumeratedType,
    Item,
    use_template,
    )
from lazr.restful.declarations import (
    call_with,
    error_status,
    export_as_webservice_entry,
    export_destructor_operation,
    export_read_operation,
    export_write_operation,
    exported,
    mutator_for,
    operation_for_version,
    operation_parameters,
    operation_returns_collection_of,
    rename_parameters_as,
    REQUEST_USER,
    )
from lazr.restful.fields import (
    CollectionField,
    Reference,
    ReferenceChoice,
    )
from lazr.restful.interface import copy_field
from zope.component import getUtility
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Choice,
    Datetime,
    Field,
    Int,
    List,
    Text,
    TextLine,
    )
from zope.schema.vocabulary import (
    SimpleTerm,
    SimpleVocabulary,
    )
from zope.security.interfaces import Unauthorized
from zope.security.proxy import isinstance as zope_isinstance

from canonical.launchpad import _
from canonical.launchpad.interfaces.launchpad import (
    IHasBug,
    IHasDateCreated,
    )
from canonical.launchpad.searchbuilder import (
    all,
    any,
    NULL,
    )
from canonical.launchpad.webapp.interfaces import ITableBatchNavigator
from lp.app.validators import LaunchpadValidationError
from lp.app.validators.name import name_validator
from lp.bugs.interfaces.bugwatch import (
    IBugWatch,
    IBugWatchSet,
    NoBugTrackerFound,
    UnrecognizedBugTrackerURL,
    )
from lp.services.fields import (
    BugField,
    PersonChoice,
    ProductNameField,
    SearchTag,
    StrippedTextLine,
    Summary,
    )
from lp.soyuz.interfaces.component import IComponent


class BugTaskImportance(DBEnumeratedType):
    """Bug Task Importance.

    Importance is used by developers and their managers to indicate how
    important fixing a bug is. Importance is typically a combination of the
    harm caused by the bug, and how often it is encountered.
    """

    UNKNOWN = DBItem(999, """
        Unknown

        The severity of this bug task is unknown.
        """)

    CRITICAL = DBItem(50, """
        Critical

        This bug is essential to fix as soon as possible. It affects
        system stability, data integrity and/or remote access
        security.
        """)

    HIGH = DBItem(40, """
        High

        This bug needs urgent attention from the maintainer or
        upstream. It affects local system security or data integrity.
        """)

    MEDIUM = DBItem(30, """
        Medium

        This bug warrants an upload just to fix it, but can be put
        off until other major or critical bugs have been fixed.
        """)

    LOW = DBItem(20, """
        Low

        This bug does not warrant an upload just to fix it, but
        it should be fixed, if possible, next time the maintainer
        does an upload. For example, it might be a typo in a document.
        """)

    WISHLIST = DBItem(10, """
        Wishlist

        This is not a bug, but a request for an enhancement or
        new feature that does not yet exist in the package. It does
        not affect system stability. For example: it might be a
        usability or documentation fix.
        """)

    UNDECIDED = DBItem(5, """
        Undecided

        A relevant developer or manager has not yet decided how
        important this bug is.
        """)


class BugTaskStatus(DBEnumeratedType):
    """Bug Task Status

    The various possible states for a bugfix in a specific place.
    """

    NEW = DBItem(10, """
        New

        This is a new bug and has not yet been confirmed by the maintainer of
        this product or source package.
        """)

    # INCOMPLETE is never actually stored now: INCOMPLETE_WITH_RESPONSE and
    # INCOMPLETE_WITHOUT_RESPONSE are mapped to INCOMPLETE on read, and on
    # write INCOMPLETE is mapped to INCOMPLETE_WITHOUT_RESPONSE. This permits
    # An index on the INCOMPLETE_WITH*_RESPONSE queries that the webapp
    # generates.
    INCOMPLETE = DBItem(15, """
        Incomplete

        More info is required before making further progress on this bug,
        likely from the reporter. E.g. the exact error message the user saw,
        the URL the user was visiting when the bug occurred, etc.
        """)

    OPINION = DBItem(16, """
        Opinion

        The bug remains open for discussion only. This status is usually
        used where there is disagreement over whether the bug is relevant
        to the current target and whether it should be fixed.
        """)

    INVALID = DBItem(17, """
        Invalid

        This is not a bug. It could be a support request, spam, or a
        misunderstanding.
        """)

    WONTFIX = DBItem(18, """
        Won't Fix

        This will not be fixed. For example, this might be a bug but it's not
        considered worth fixing, or it might not be fixed in this release.
        """)

    EXPIRED = DBItem(19, """
        Expired

        This bug is expired. There was no activity for a long time.
        """)

    CONFIRMED = DBItem(20, """
        Confirmed

        This bug has been reviewed, verified, and confirmed as something
        needing fixing. Anyone can set this status.
        """)

    TRIAGED = DBItem(21, """
        Triaged

        This bug has been reviewed, verified, and confirmed as
        something needing fixing. The user must be a bug supervisor to
        set this status, so it carries more weight than merely
        Confirmed.
        """)

    INPROGRESS = DBItem(22, """
        In Progress

        The person assigned to fix this bug is currently working on fixing it.
        """)

    FIXCOMMITTED = DBItem(25, """
        Fix Committed

        This bug has been fixed in version control, but the fix has
        not yet made it into a released version of the affected
        software.
        """)

    FIXRELEASED = DBItem(30, """
        Fix Released

        The fix for this bug is available in a released version of the
        affected software.
        """)

    UNKNOWN = DBItem(999, """
        Unknown

        The status of this bug task is unknown.
        """)


class BugTaskStatusSearch(DBEnumeratedType):
    """Bug Task Status

    The various possible states for a bugfix in searches.
    """
    use_template(BugTaskStatus, exclude=('UNKNOWN'))

    INCOMPLETE_WITH_RESPONSE = DBItem(13, """
        Incomplete (with response)

        This bug has new information since it was last marked
        as requiring a response.
        """)

    INCOMPLETE_WITHOUT_RESPONSE = DBItem(14, """
        Incomplete (without response)

        This bug requires more information, but no additional
        details were supplied yet..
        """)


def get_bugtask_status(status_id):
    """Get a member of `BugTaskStatus` or `BugTaskStatusSearch` by value.

    `BugTaskStatus` and `BugTaskStatusSearch` intersect, but neither is a
    subset of the other, so this searches first in `BugTaskStatus` then in
    `BugTaskStatusSearch` for a member with the given ID.
    """
    try:
        return BugTaskStatus.items[status_id]
    except KeyError:
        return BugTaskStatusSearch.items[status_id]


def normalize_bugtask_status(status):
    """Normalize `status`.

    It might be a member of any of three related enums: `BugTaskStatus`,
    `BugTaskStatusSearch`, or `BugTaskStatusSearchDisplay`. This tries to
    normalize by value back to the first of those three enums in which the
    status appears.
    """
    try:
        return BugTaskStatus.items[status.value]
    except KeyError:
        return BugTaskStatusSearch.items[status.value]


class BugTagsSearchCombinator(EnumeratedType):
    """Bug Tags Search Combinator

    The possible values for combining the list of tags in a bug search.
    """

    ANY = Item("""
        Any

        Search for bugs tagged with any of the specified tags.
        """)

    ALL = Item("""
        All

        Search for bugs tagged with all of the specified tags.
        """)


class BugTaskStatusSearchDisplay(DBEnumeratedType):
    """Bug Task Status

    The various possible states for a bugfix in advanced
    bug search forms.
    """
    use_template(BugTaskStatusSearch, exclude=('INCOMPLETE'))


class BugBranchSearch(EnumeratedType):
    """Bug branch search option.

    The possible values to search for bugs having branches attached
    or not having branches attached.
    """

    ALL = Item("Show all bugs")

    BUGS_WITH_BRANCHES = Item("Show only Bugs with linked Branches")

    BUGS_WITHOUT_BRANCHES = Item("Show only Bugs without linked Branches")


class BugBlueprintSearch(EnumeratedType):
    """Bug blueprint search option.

    The possible values to search for bugs having blueprints attached
    or not having blueprints attached.
    """

    ALL = Item("Show all bugs")

    BUGS_WITH_BLUEPRINTS = Item("Show only Bugs with linked Blueprints")

    BUGS_WITHOUT_BLUEPRINTS = Item("Show only Bugs without linked Blueprints")


UNRESOLVED_BUGTASK_STATUSES = (
    BugTaskStatus.NEW,
    BugTaskStatus.INCOMPLETE,
    BugTaskStatus.CONFIRMED,
    BugTaskStatus.TRIAGED,
    BugTaskStatus.INPROGRESS,
    BugTaskStatus.FIXCOMMITTED)

# Actual values stored in the DB:
DB_INCOMPLETE_BUGTASK_STATUSES = (
    BugTaskStatusSearch.INCOMPLETE_WITH_RESPONSE,
    BugTaskStatusSearch.INCOMPLETE_WITHOUT_RESPONSE,
    )

DB_UNRESOLVED_BUGTASK_STATUSES = (
    UNRESOLVED_BUGTASK_STATUSES +
    DB_INCOMPLETE_BUGTASK_STATUSES
    )

RESOLVED_BUGTASK_STATUSES = (
    BugTaskStatus.FIXRELEASED,
    BugTaskStatus.OPINION,
    BugTaskStatus.INVALID,
    BugTaskStatus.WONTFIX,
    BugTaskStatus.EXPIRED)

BUG_SUPERVISOR_BUGTASK_STATUSES = (
    BugTaskStatus.WONTFIX,
    BugTaskStatus.EXPIRED,
    BugTaskStatus.TRIAGED)

DEFAULT_SEARCH_BUGTASK_STATUSES = (
    BugTaskStatusSearch.NEW,
    BugTaskStatusSearch.INCOMPLETE_WITH_RESPONSE,
    BugTaskStatusSearch.INCOMPLETE_WITHOUT_RESPONSE,
    BugTaskStatusSearch.CONFIRMED,
    BugTaskStatusSearch.TRIAGED,
    BugTaskStatusSearch.INPROGRESS,
    BugTaskStatusSearch.FIXCOMMITTED)

DEFAULT_SEARCH_BUGTASK_STATUSES_FOR_DISPLAY = [
    BugTaskStatusSearchDisplay.items.mapping[item.value]
    for item in DEFAULT_SEARCH_BUGTASK_STATUSES]


@error_status(httplib.BAD_REQUEST)
class CannotDeleteBugtask(Exception):
    """The bugtask cannot be deleted.

    Raised when a user tries to delete a bugtask but the deletion cannot
    proceed because of a model constraint or other business rule violation.
    """


@error_status(httplib.UNAUTHORIZED)
class UserCannotEditBugTaskStatus(Unauthorized):
    """User not permitted to change status.

    Raised when a user tries to transition to a new status who doesn't
    have the necessary permissions.
    """


@error_status(httplib.UNAUTHORIZED)
class UserCannotEditBugTaskImportance(Unauthorized):
    """User not permitted to change importance.

    Raised when a user tries to transition to a new importance who
    doesn't have the necessary permissions.
    """


@error_status(httplib.UNAUTHORIZED)
class UserCannotEditBugTaskMilestone(Unauthorized):
    """User not permitted to change milestone.

    Raised when a user tries to transition to a milestone who doesn't have
    the necessary permissions.
    """


@error_status(httplib.UNAUTHORIZED)
class UserCannotEditBugTaskAssignee(Unauthorized):
    """User not permitted to change bugtask assignees.

    Raised when a user with insufficient prilieges tries to set
    the assignee of a bug task.
    """


@error_status(httplib.BAD_REQUEST)
class IllegalTarget(Exception):
    """Exception raised when trying to set an illegal bug task target."""


@error_status(httplib.BAD_REQUEST)
class IllegalRelatedBugTasksParams(Exception):
    """Exception raised when trying to overwrite all relevant parameters
    in a search for related bug tasks"""


class IBugTaskDelete(Interface):
    """An interface for operations allowed with the Delete permission."""
    @export_destructor_operation()
    @call_with(who=REQUEST_USER)
    @operation_for_version('devel')
    def delete(who):
        """Delete this bugtask.

        :param who: the user who is removing the bugtask.
        :raises: CannotDeleteBugtask if the bugtask cannot be deleted due to a
            business rule or other model constraint.
        :raises: Unauthorized if the user does not have permission
            to delete the bugtask.
        """


class IBugTask(IHasDateCreated, IHasBug, IBugTaskDelete):
    """A bug needing fixing in a particular product or package."""
    export_as_webservice_entry()

    id = Int(title=_("Bug Task #"))
    bug = exported(
        BugField(title=_("Bug"), readonly=True))
    product = Choice(
        title=_('Project'), required=False, vocabulary='Product')
    productID = Attribute('The product ID')
    productseries = Choice(
        title=_('Series'), required=False, vocabulary='ProductSeries')
    productseriesID = Attribute('The product series ID')
    sourcepackagename = Choice(
        title=_("Package"), required=False,
        vocabulary='SourcePackageName')
    sourcepackagenameID = Attribute('The sourcepackagename ID')
    distribution = Choice(
        title=_("Distribution"), required=False, vocabulary='Distribution')
    distributionID = Attribute('The distribution ID')
    distroseries = Choice(
        title=_("Series"), required=False,
        vocabulary='DistroSeries')
    distroseriesID = Attribute('The distroseries ID')
    milestone = exported(ReferenceChoice(
        title=_('Milestone'),
        required=False,
        readonly=True,
        vocabulary='Milestone',
        schema=Interface))  # IMilestone
    milestoneID = Attribute('The id of the milestone.')

    # The status and importance's vocabularies do not
    # contain an UNKNOWN item in bugtasks that aren't linked to a remote
    # bugwatch; this would be better described in a separate interface,
    # but adding a marker interface during initialization is expensive,
    # and adding it post-initialization is not trivial.
    # Note that status is a property because the model only exposes INCOMPLETE
    # but the DB stores INCOMPLETE_WITH_RESPONSE and
    # INCOMPLETE_WITHOUT_RESPONSE for query efficiency.
    status = exported(
        Choice(title=_('Status'), vocabulary=BugTaskStatus,
               default=BugTaskStatus.NEW, readonly=True))
    _status = Attribute('The actual status DB column used in queries.')
    importance = exported(
        Choice(title=_('Importance'), vocabulary=BugTaskImportance,
               default=BugTaskImportance.UNDECIDED, readonly=True))
    assignee = exported(
        PersonChoice(
            title=_('Assigned to'), required=False,
            vocabulary='ValidAssignee',
            readonly=True))
    assigneeID = Attribute('The assignee ID (for eager loading)')
    bugtargetdisplayname = exported(
        Text(title=_("The short, descriptive name of the target"),
             readonly=True),
        exported_as='bug_target_display_name')
    bugtargetname = exported(
        Text(title=_("The target as presented in mail notifications"),
             readonly=True),
        exported_as='bug_target_name')
    bugwatch = exported(
        ReferenceChoice(
            title=_("Remote Bug Details"), required=False,
            schema=IBugWatch,
            vocabulary='BugWatch', description=_(
                "Select the bug watch that "
                "represents this task in the relevant bug tracker. If none "
                "of the bug watches represents this particular bug task, "
                "leave it as (None). Linking the remote bug watch with the "
                "task in this way means that a change in the remote bug "
                "status will change the status of this bug task in "
                "Launchpad.")),
        exported_as='bug_watch')
    date_assigned = exported(
        Datetime(title=_("Date Assigned"),
                 description=_("The date on which this task was assigned "
                               "to someone."),
                 readonly=True,
                 required=False))
    datecreated = exported(
        Datetime(title=_("Date Created"),
                 description=_("The date on which this task was created."),
                 readonly=True),
        exported_as='date_created')
    date_confirmed = exported(
        Datetime(title=_("Date Confirmed"),
                 description=_("The date on which this task was marked "
                               "Confirmed."),
                 readonly=True,
                 required=False))
    date_incomplete = exported(
        Datetime(title=_("Date Incomplete"),
                 description=_("The date on which this task was marked "
                               "Incomplete."),
                 readonly=True,
                 required=False))
    date_inprogress = exported(
        Datetime(title=_("Date In Progress"),
                 description=_("The date on which this task was marked "
                               "In Progress."),
                 readonly=True,
                 required=False),
        exported_as='date_in_progress')
    date_closed = exported(
        Datetime(title=_("Date Closed"),
                 description=_("The date on which this task was marked "
                               "either Won't Fix, Invalid or Fix Released."),
                 readonly=True,
                 required=False))
    date_left_new = exported(
        Datetime(title=_("Date left new"),
                 description=_("The date on which this task was marked "
                               "with a status higher than New."),
                 readonly=True,
                 required=False))
    date_triaged = exported(
        Datetime(title=_("Date Triaged"),
                 description=_("The date on which this task was marked "
                               "Triaged."),
                 readonly=True,
                 required=False))
    date_fix_committed = exported(
        Datetime(title=_("Date Fix Committed"),
                 description=_("The date on which this task was marked "
                               "Fix Committed."),
                 readonly=True,
                 required=False))
    date_fix_released = exported(
        Datetime(title=_("Date Fix Released"),
                 description=_("The date on which this task was marked "
                               "Fix Released."),
                 readonly=True,
                 required=False))
    date_left_closed = exported(
        Datetime(title=_("Date left closed"),
                 description=_("The date on which this task was "
                               "last reopened."),
                 readonly=True,
                 required=False))
    age = Datetime(title=_("Age"),
                   description=_("The age of this task, expressed as the "
                                 "length of time between the creation date "
                                 "and now."))
    task_age = Int(title=_("Age of the bug task"),
            description=_("The age of this task in seconds, a delta between "
                         "now and the date the bug task was created."))
    owner = exported(
        Reference(title=_("The owner"), schema=Interface, readonly=True))
    target = exported(Reference(
        title=_('Target'), required=True, schema=Interface,  # IBugTarget
        readonly=True,
        description=_("The software in which this bug should be fixed.")))
    target_uses_malone = Bool(
        title=_("Whether the bugtask's target uses Launchpad officially"))
    title = exported(
        Text(title=_("The title of the bug related to this bugtask"),
             readonly=True))
    related_tasks = exported(
        CollectionField(
            description=_(
                "IBugTasks related to this one, namely other "
                "IBugTasks on the same IBug."),
            value_type=Reference(schema=Interface),  # Will be specified later
            readonly=True))
    pillar = Choice(
        title=_('Pillar'),
        description=_("The LP pillar (product or distribution) "
                      "associated with this task."),
        vocabulary='DistributionOrProduct', readonly=True)
    other_affected_pillars = Attribute(
        "The other pillars (products or distributions) affected by this bug. "
        "This returns a list of pillars OTHER THAN the pillar associated "
        "with this particular bug.")
    # This property does various database queries. It is a property so a
    # "snapshot" of its value will be taken when a bugtask is modified, which
    # allows us to compare it to the current value and see if there are any
    # new subscribers that should get an email containing full bug details
    # (rather than just the standard change mail.) It is a property on
    # IBugTask because we currently only ever need this value for events
    # handled on IBugTask.
    bug_subscribers = Field(
        title=_("A list of IPersons subscribed to the bug, whether directly "
                "or indirectly."), readonly=True)

    conjoined_master = Attribute(
        "The series-specific bugtask in a conjoined relationship")
    conjoined_slave = Attribute(
        "The generic bugtask in a conjoined relationship")

    is_complete = exported(
        Bool(description=_(
                "True or False depending on whether or not there is more "
                "work required on this bug task."),
             readonly=True))

    def userCanDelete(user):
        """Check that a user may delete a bugtask.

        A user may delete a bugtask if:
         - The disclosure.delete_bugtask.enabled feature flag is enabled,
         and they are:
         - project maintainer
         - task creator
         - bug supervisor
        """

    @operation_returns_collection_of(Interface)  # Actually IBug.
    @call_with(user=REQUEST_USER, limit=10)
    @export_read_operation()
    def findSimilarBugs(user, limit=10):
        """Return the list of possible duplicates for this BugTask."""

    @call_with(user=REQUEST_USER)
    @operation_parameters(person=copy_field(assignee))
    @export_read_operation()
    @operation_for_version("devel")
    def getContributorInfo(user, person):
        """Is the person a contributor to bugs in this task's pillar?

        :param user: The user doing the search. Private bugs that this
            user doesn't have access to won't be included in the search.
        :param person: The person to check to see if they are a contributor.

        Return a dict with the following values:
        is_contributor: True if the user has any bugs assigned to him in the
        context of this bug task's pillar, either directly or by team
        participation.
        person_name: the displayname of the person
        pillar_name: the displayname of the bug task's pillar

        This API call is provided for use by the client Javascript where the
        calling context does not have access to the person or pillar names.
        """

    def getConjoinedMaster(bugtasks, bugtasks_by_package=None):
        """Return the conjoined master in the given bugtasks, if any.

        :param bugtasks: The bugtasks to be considered when looking for
            the conjoined master.
        :param bugtasks_by_package: A cache, mapping a
            `ISourcePackageName` to a list of bug tasks targeted to such
            a package name. Both distribution and distro series tasks
            should be included in this list.

        This method exists mainly to allow calculating the conjoined
        master from a cached list of bug tasks, reducing the number of
        db queries needed.
        """

    def subscribe(person, subscribed_by):
        """Subscribe this person to the underlying bug.

        This method was documented as being required here so that
        MentorshipOffers could happen on IBugTask. If that was the sole reason
        this method should be deletable. When we move to context-less bug
        presentation (where the bug is at /bugs/n?task=ubuntu) then we can
        eliminate this if it is no longer useful.
        """

    def isSubscribed(person):
        """Return True if the person is an explicit subscriber to the
        underlying bug for this bugtask.

        This method was documented as being required here so that
        MentorshipOffers could happen on IBugTask. If that was the sole
        reason then this method should be deletable.  When we move to
        context-less bug presentation (where the bug is at
        /bugs/n?task=ubuntu) then we can eliminate this if it is no
        longer useful.
        """

    @mutator_for(milestone)
    @rename_parameters_as(new_milestone='milestone')
    @operation_parameters(new_milestone=copy_field(milestone))
    @call_with(user=REQUEST_USER)
    @export_write_operation()
    def transitionToMilestone(new_milestone, user):
        """Set the BugTask milestone.

        Set the bugtask milestone, making sure that the user is
        authorised to do so.
        """

    @mutator_for(importance)
    @rename_parameters_as(new_importance='importance')
    @operation_parameters(new_importance=copy_field(importance))
    @call_with(user=REQUEST_USER)
    @export_write_operation()
    def transitionToImportance(new_importance, user):
        """Set the BugTask importance.

        Set the bugtask importance, making sure that the user is
        authorised to do so.
        """

    def setImportanceFromDebbugs(severity):
        """Set the Launchpad BugTask importance on the basis of a debbugs
        severity.  This maps from the debbugs severity values ('normal',
        'important', 'critical', 'serious', 'minor', 'wishlist', 'grave') to
        the Launchpad importance values, and returns the relevant Launchpad
        importance.
        """

    def canTransitionToStatus(new_status, user):
        """Return True if the user is allowed to change the status to
        `new_status`.

        :new_status: new status from `BugTaskStatus`
        :user: the user requesting the change

        Some status transitions, e.g. Triaged, require that the user
        be a bug supervisor or the owner of the project.
        """

    @mutator_for(status)
    @rename_parameters_as(new_status='status')
    @operation_parameters(
        new_status=copy_field(status))
    @call_with(user=REQUEST_USER)
    @export_write_operation()
    def transitionToStatus(new_status, user):
        """Perform a workflow transition to the new_status.

        :new_status: new status from `BugTaskStatus`
        :user: the user requesting the change

        For certain statuses, e.g. Confirmed, other actions will
        happen, like recording the date when the task enters this
        status.

        Some status transitions require extra conditions to be met.
        See `canTransitionToStatus` for more details.
        """

    def userCanSetAnyAssignee(user):
        """Check if the current user can set anybody sa a bugtask assignee.

        Owners, drivers, bug supervisors and Launchpad admins can always
        assign to someone else.  Other users can assign to someone else if a
        bug supervisor is not defined.
        """

    def userCanUnassign(user):
        """Check if the current user can set assignee to None.

        Project owner, project drivers, series drivers, bug supervisors
        and Launchpad admins can do this always; other users can do this
        only if they or their reams are the assignee.
        """

    @mutator_for(assignee)
    @operation_parameters(
        assignee=copy_field(assignee))
    @export_write_operation()
    def transitionToAssignee(assignee):
        """Perform a workflow transition to the given assignee.

        When the bugtask assignee is changed from None to an IPerson
        object, the date_assigned is set on the task. If the assignee
        value is set to None, date_assigned is also set to None.
        """

    def validateTransitionToTarget(target):
        """Check whether a transition to this target is legal.

        :raises IllegalTarget: if the new target is not allowed.
        """

    @mutator_for(target)
    @operation_parameters(
        target=copy_field(target))
    @export_write_operation()
    def transitionToTarget(target):
        """Convert the bug task to a different bug target."""

    def updateTargetNameCache():
        """Update the targetnamecache field in the database.

        This method is meant to be called when an IBugTask is created or
        modified and will also be called from the update_stats.py cron script
        to ensure that the targetnamecache is properly updated when, for
        example, an IDistribution is renamed.
        """

    def asEmailHeaderValue():
        """Return a value suitable for an email header value for this bugtask.

        The return value is a single line of arbitrary length, so header
        folding should be done by the callsite, as needed.

        For an upstream task, this value might look like:

          product=firefox; status=New; importance=Critical; assignee=None;

        See doc/bugmail-headers.txt for a complete explanation and more
        examples.
        """

    def getDelta(old_task):
        """Compute the delta from old_task to this task.

        Returns an IBugTaskDelta or None if there were no changes between
        old_task and this task.
        """

    def getPackageComponent():
        """Return the task's package's component or None.

        Returns the component associated to the current published
        package in that distribution's current series. If the task is
        not a package task, returns None.
        """

    def userCanEditMilestone(user):
        """Can the user edit the Milestone field?"""

    def userCanEditImportance(user):
        """Can the user edit the Importance field?"""


# Set schemas that were impossible to specify during the definition of
# IBugTask itself.
IBugTask['related_tasks'].value_type.schema = IBugTask

# We are forced to define this now to avoid circular import problems.
IBugWatch['bugtasks'].value_type.schema = IBugTask


UPSTREAM_STATUS_VOCABULARY = SimpleVocabulary(
    [SimpleTerm(
        "pending_bugwatch",
        title="Show bugs that need to be forwarded to an upstream "
              "bug tracker"),
    SimpleTerm(
        "hide_upstream",
        title="Show bugs that are not known to affect upstream"),
    SimpleTerm(
        "resolved_upstream",
        title="Show bugs that are resolved upstream"),
    SimpleTerm(
        "open_upstream",
        title="Show bugs that are open upstream"),
    ])

UPSTREAM_PRODUCT_STATUS_VOCABULARY = SimpleVocabulary(
    [SimpleTerm(
        "pending_bugwatch",
        title="Show bugs that need to be forwarded to an upstream bug "
              "tracker"),
    SimpleTerm(
        "resolved_upstream",
        title="Show bugs that are resolved elsewhere"),
    ])


class IBugTaskSearchBase(Interface):
    """The basic search controls."""
    searchtext = TextLine(title=_("Bug ID or search text."), required=False)
    status = List(
        title=_('Status'),
        description=_('Show only bugs with the given status value '
                      'or list of values.'),
        value_type=Choice(
            title=_('Status'),
            vocabulary=BugTaskStatusSearch,
            default=BugTaskStatusSearch.NEW),
        default=list(DEFAULT_SEARCH_BUGTASK_STATUSES),
        required=False)
    importance = List(
        title=_('Importance'),
        description=_('Show only bugs with the given importance '
                      'or list of importances.'),
        value_type=IBugTask['importance'],
        required=False)
    assignee = Choice(
        title=_('Assignee'),
        description=_('Person entity assigned for this bug.'),
        vocabulary='ValidAssignee', required=False)
    bug_reporter = Choice(
        title=_('Bug reporter'),
        description=_('Person entity that filed the bug report.'),
        vocabulary='ValidAssignee', required=False)
    omit_dupes = Bool(
        title=_('Omit bugs marked as duplicate,'), required=False,
        default=True)
    omit_targeted = Bool(
        title=_('Omit bugs targeted to a series'), required=False,
        default=True)
    has_patch = Bool(
        title=_('Show only bugs with patches available.'), required=False,
        default=False)
    has_no_package = Bool(
        title=_('Exclude bugs with packages specified'),
        required=False, default=False)
    milestone_assignment = Choice(
        title=_('Target'), vocabulary="Milestone", required=False)
    milestone = List(
        title=_('Milestone'),
        description=_('Show only bug tasks targeted to this milestone.'),
        value_type=IBugTask['milestone'], required=False)
    component = List(
        title=_('Component'),
        description=_('Distribution package archive grouping. '
                      'E.g. main, universe, multiverse'),
        value_type=IComponent['name'], required=False)
    tag = List(title=_("Tag"), value_type=SearchTag(), required=False)
    status_upstream = List(
        title=_('Status upstream'),
        description=_('Indicates the status of any remote watches '
                      'associated with the bug.  Possible values '
                      'include: pending_bugwatch, hide_upstream, '
                      'resolved_upstream, and open_upstream.'),
        value_type=Choice(vocabulary=UPSTREAM_STATUS_VOCABULARY),
        required=False)
    has_cve = Bool(
        title=_('Show only bugs associated with a CVE'), required=False)
    bug_supervisor = Choice(
        title=_('Bug supervisor'), vocabulary='ValidPersonOrTeam',
        description=_('Show only bugs in packages this person or team '
                      'is subscribed to.'),
        required=False)
    bug_commenter = Choice(
        title=_('Bug commenter'), vocabulary='ValidPersonOrTeam',
        description=_('Show only bugs commented on by this person.'),
        required=False)
    subscriber = Choice(
        title=_('Bug subscriber'), vocabulary='ValidPersonOrTeam',
        description=_('Show only bugs this person or team '
                      'is directly subscribed to.'),
        required=False)
    affects_me = Bool(
        title=_('Show only bugs affecting me'), required=False)
    has_branches = Bool(
        title=_('Show bugs with linked branches'), required=False,
        default=True)
    has_no_branches = Bool(
        title=_('Show bugs without linked branches'), required=False,
        default=True)
    has_blueprints = Bool(
        title=_('Show bugs with linked blueprints'), required=False,
        default=True)
    has_no_blueprints = Bool(
        title=_('Show bugs without linked blueprints'), required=False,
        default=True)


class IBugTaskSearch(IBugTaskSearchBase):
    """The schema used by a bug task search form not on a Person.

    Note that this is slightly different than simply IBugTask because
    some of the field types are different (e.g. it makes sense for
    status to be a Choice on a bug task edit form, but it makes sense
    for status to be a List field on a search form, where more than
    one value can be selected.)
    """
    tag = List(
        title=_("Tags"),
        description=_("String or list of strings for tags to search. "
                      "To exclude, prepend a '-', e.g. '-unwantedtag'"),
        value_type=SearchTag(), required=False)
    tags_combinator = Choice(
        title=_("Tags combination"),
        description=_("Search for any or all of the tags specified."),
        vocabulary=BugTagsSearchCombinator, required=False,
        default=BugTagsSearchCombinator.ANY)


class IPersonBugTaskSearch(IBugTaskSearchBase):
    """The schema used by the bug task search form of a person."""
    sourcepackagename = Choice(
        title=_("Source Package Name"), required=False,
        description=_("The source package in which the bug occurs. "
        "Leave blank if you are not sure."),
        vocabulary='SourcePackageName')
    distribution = Choice(
        title=_("Distribution"), required=False, vocabulary='Distribution')
    tags_combinator = Choice(
        title=_("Tags combination"),
        description=_("Search for any or all of the tags specified."),
        vocabulary=BugTagsSearchCombinator, required=False,
        default=BugTagsSearchCombinator.ANY)


class IUpstreamProductBugTaskSearch(IBugTaskSearch):
    """The schema used by the bug task search form for upstream products.

    This schema is the same as IBugTaskSearch, except that it has only
    one choice for Status Upstream.
    """
    status_upstream = List(
        title=_('Status Upstream'),
        value_type=Choice(
            vocabulary=UPSTREAM_PRODUCT_STATUS_VOCABULARY),
        required=False)


class IFrontPageBugTaskSearch(IBugTaskSearchBase):
    """Additional search options for the front page of bugs."""
    scope = Choice(
        title=u"Search Scope", required=False,
        vocabulary="DistributionOrProductOrProjectGroup")


class IBugTaskDelta(Interface):
    """The change made to a bug task (e.g. in an edit screen).

    If product is not None, the sourcepackagename must be None.

    Likewise, if sourcepackagename is not None, product must be None.
    """
    bugtask = Attribute("The modified IBugTask.")
    target = Attribute(
        """The change made to the IBugTarget for this task.

        The value is a dict like {'old' : IBugTarget, 'new' : IBugTarget},
        or None, if no change was made to the target.
        """)
    status = Attribute(
        """The change made to the status for this task.

        The value is a dict like
        {'old' : BugTaskStatus.FOO, 'new' : BugTaskStatus.BAR}, or None,
        if no change was made to the status.
        """)
    importance = Attribute(
        """The change made to the importance of this task.

        The value is a dict like
        {'old' : BugTaskImportance.FOO, 'new' : BugTaskImportance.BAR},
        or None, if no change was made to the importance.
        """)
    assignee = Attribute(
        """The change made to the assignee of this task.

        The value is a dict like {'old' : IPerson, 'new' : IPerson}, or None,
        if no change was made to the assignee.
        """)
    bugwatch = Attribute("The bugwatch which governs this task.")
    milestone = Attribute("The milestone for which this task is scheduled.")


class BugTaskSearchParams:
    """Encapsulates search parameters for BugTask.search()

    Details:

      user is an object that provides IPerson, and represents the
      person performing the query (which is important to know for, for
      example, privacy-aware results.) If user is None, the search
      will be filtered to only consider public bugs.

      product, distribution and distroseries (IBugTargets) should /not/
      be supplied to BugTaskSearchParams; instead, IBugTarget's
      searchTasks() method should be invoked with a single search_params
      argument.

      Keyword arguments should always be used. The argument passing
      semantics are as follows:

        * BugTaskSearchParams(arg='foo', user=bar): Match all IBugTasks
          where IBugTask.arg == 'foo' for user bar.

        * BugTaskSearchParams(arg=any('foo', 'bar')): Match all
          IBugTasks where IBugTask.arg == 'foo' or IBugTask.arg ==
          'bar'. In this case, no user was passed, so all private bugs
          are excluded from the search results.

        * BugTaskSearchParams(arg1='foo', arg2='bar'): Match all
          IBugTasks where IBugTask.arg1 == 'foo' and IBugTask.arg2 ==
          'bar'

    The set will be ordered primarily by the column specified in orderby,
    and then by bugtask id.

    For a more thorough treatment, check out:

        lib/lp/bugs/doc/bugtask-search.txt
    """

    product = None
    project = None
    distribution = None
    distroseries = None
    productseries = None

    def __init__(self, user, bug=None, searchtext=None, fast_searchtext=None,
                 status=None, importance=None, milestone=None,
                 assignee=None, sourcepackagename=None, owner=None,
                 attachmenttype=None, orderby=None, omit_dupes=False,
                 subscriber=None, component=None,
                 pending_bugwatch_elsewhere=False, resolved_upstream=False,
                 open_upstream=False, has_no_upstream_bugtask=False, tag=None,
                 has_cve=False, bug_supervisor=None, bug_reporter=None,
                 nominated_for=None, bug_commenter=None, omit_targeted=False,
                 date_closed=None, affected_user=None, affects_me=False,
                 hardware_bus=None, hardware_vendor_id=None,
                 hardware_product_id=None, hardware_driver_name=None,
                 hardware_driver_package_name=None,
                 hardware_owner_is_bug_reporter=None,
                 hardware_owner_is_affected_by_bug=False,
                 hardware_owner_is_subscribed_to_bug=False,
                 hardware_is_linked_to_bug=False,
                 linked_branches=None, linked_blueprints=None,
                 structural_subscriber=None, modified_since=None,
                 created_since=None, exclude_conjoined_tasks=False, cve=None):

        self.bug = bug
        self.searchtext = searchtext
        self.fast_searchtext = fast_searchtext
        self.status = status
        self.importance = importance
        self.milestone = milestone
        self.assignee = assignee
        self.sourcepackagename = sourcepackagename
        self.owner = owner
        self.attachmenttype = attachmenttype
        self.user = user
        self.orderby = orderby
        self.omit_dupes = omit_dupes
        self.omit_targeted = omit_targeted
        self.subscriber = subscriber
        self.component = component
        self.pending_bugwatch_elsewhere = pending_bugwatch_elsewhere
        self.resolved_upstream = resolved_upstream
        self.open_upstream = open_upstream
        self.has_no_upstream_bugtask = has_no_upstream_bugtask
        self.tag = tag
        self.has_cve = has_cve
        self.bug_supervisor = bug_supervisor
        self.bug_reporter = bug_reporter
        self.nominated_for = nominated_for
        self.bug_commenter = bug_commenter
        self.date_closed = date_closed
        self.affected_user = affected_user
        self.affects_me = affects_me
        self.hardware_bus = hardware_bus
        self.hardware_vendor_id = hardware_vendor_id
        self.hardware_product_id = hardware_product_id
        self.hardware_driver_name = hardware_driver_name
        self.hardware_driver_package_name = hardware_driver_package_name
        self.hardware_owner_is_bug_reporter = hardware_owner_is_bug_reporter
        self.hardware_owner_is_affected_by_bug = (
            hardware_owner_is_affected_by_bug)
        self.hardware_owner_is_subscribed_to_bug = (
            hardware_owner_is_subscribed_to_bug)
        self.hardware_is_linked_to_bug = hardware_is_linked_to_bug
        self.linked_branches = linked_branches
        self.linked_blueprints = linked_blueprints
        self.structural_subscriber = structural_subscriber
        self.modified_since = modified_since
        self.created_since = created_since
        self.exclude_conjoined_tasks = exclude_conjoined_tasks
        self.cve = cve

    def setProduct(self, product):
        """Set the upstream context on which to filter the search."""
        self.product = product

    def setProject(self, project):
        """Set the upstream context on which to filter the search."""
        self.project = project

    def setDistribution(self, distribution):
        """Set the distribution context on which to filter the search."""
        self.distribution = distribution

    def setDistroSeries(self, distroseries):
        """Set the distroseries context on which to filter the search."""
        self.distroseries = distroseries

    def setProductSeries(self, productseries):
        """Set the productseries context on which to filter the search."""
        self.productseries = productseries

    def setSourcePackage(self, sourcepackage):
        """Set the sourcepackage context on which to filter the search."""
        # Import this here to avoid circular dependencies
        from lp.registry.interfaces.sourcepackage import (
            ISourcePackage)
        if isinstance(sourcepackage, any):
            # Unwrap the source package.
            self.sourcepackagename = any(*[
                pkg.sourcepackagename for pkg in sourcepackage.query_values])
            distroseries = any(*[pkg.distroseries for pkg in
                sourcepackage.query_values if ISourcePackage.providedBy(pkg)])
            distributions = any(*[pkg.distribution for pkg in
                sourcepackage.query_values
                if not ISourcePackage.providedBy(pkg)])
            if distroseries.query_values and not distributions.query_values:
                self.distroseries = distroseries
            elif not distroseries.query_values and distributions.query_values:
                self.distributions = distributions
            else:
                # At this point we have determined that either we have both
                # distroseries and distributions, or we have neither of them.
                # We will set both.  Doing so will give us the cross-product,
                # because searching source packages is
                # sourcepackagename-specific rather than actually
                # context-specific. This is not ideal but is tolerable given
                # no actual use of mixed-type any() exists today.
                self.distroseries = distroseries
                self.distributions = distributions
            return
        if ISourcePackage.providedBy(sourcepackage):
            # This is a sourcepackage in a distro series.
            self.distroseries = sourcepackage.distroseries
        else:
            # This is a sourcepackage in a distribution.
            self.distribution = sourcepackage.distribution
        self.sourcepackagename = sourcepackage.sourcepackagename

    def setTarget(self, target):
        """Constrain the search to only return items in target.

        This is equivalent to calling setProduct etc but the type of target
        does not need to be known to the caller.

        :param target: A `IHasBug`, or some search term like all/any/none on
            `IHasBug`. If using all/any all the targets must be of the
            same type due to implementation limitations. Currently only
            distroseries and productseries `IHasBug` implementations are
            supported.
        """
        # Yay circular deps.
        from lp.registry.interfaces.distribution import IDistribution
        from lp.registry.interfaces.distroseries import IDistroSeries
        from lp.registry.interfaces.product import IProduct
        from lp.registry.interfaces.productseries import IProductSeries
        from lp.registry.interfaces.milestone import IMilestone
        from lp.registry.interfaces.projectgroup import IProjectGroup
        from lp.registry.interfaces.sourcepackage import ISourcePackage
        from lp.registry.interfaces.distributionsourcepackage import \
            IDistributionSourcePackage
        if isinstance(target, (any, all)):
            assert len(target.query_values), \
                'cannot determine target with no targets'
            instance = target.query_values[0]
        else:
            instance = target
        if IDistribution.providedBy(instance):
            self.setDistribution(target)
        elif IDistroSeries.providedBy(instance):
            self.setDistroSeries(target)
        elif IProduct.providedBy(instance):
            self.setProduct(target)
        elif IProductSeries.providedBy(instance):
            self.setProductSeries(target)
        elif IMilestone.providedBy(instance):
            self.milestone = target
        elif ISourcePackage.providedBy(instance):
            self.setSourcePackage(target)
        elif IDistributionSourcePackage.providedBy(instance):
            self.setSourcePackage(target)
        elif IProjectGroup.providedBy(instance):
            self.setProject(target)
        else:
            raise AssertionError("unknown target type %r" % target)

    @classmethod
    def _anyfy(cls, value):
        """If value is a sequence, wrap its items with the `any` combinator.

        Otherwise, return value as is, or None if it's a zero-length sequence.
        """
        if zope_isinstance(value, (list, tuple)):
            if len(value) > 1:
                return any(*value)
            elif len(value) == 1:
                return value[0]
            else:
                return None
        else:
            return value

    @classmethod
    def fromSearchForm(cls, user,
                       order_by=('-importance', ), search_text=None,
                       status=list(UNRESOLVED_BUGTASK_STATUSES),
                       importance=None,
                       assignee=None, bug_reporter=None, bug_supervisor=None,
                       bug_commenter=None, bug_subscriber=None, owner=None,
                       affected_user=None, affects_me=False,
                       has_patch=None, has_cve=None,
                       distribution=None, tags=None,
                       tags_combinator=BugTagsSearchCombinator.ALL,
                       omit_duplicates=True, omit_targeted=None,
                       status_upstream=None, milestone_assignment=None,
                       milestone=None, component=None, nominated_for=None,
                       sourcepackagename=None, has_no_package=None,
                       hardware_bus=None, hardware_vendor_id=None,
                       hardware_product_id=None, hardware_driver_name=None,
                       hardware_driver_package_name=None,
                       hardware_owner_is_bug_reporter=None,
                       hardware_owner_is_affected_by_bug=False,
                       hardware_owner_is_subscribed_to_bug=False,
                       hardware_is_linked_to_bug=False, linked_branches=None,
                       linked_blueprints=None, structural_subscriber=None,
                       modified_since=None, created_since=None):
        """Create and return a new instance using the parameter list."""
        search_params = cls(user=user, orderby=order_by)

        search_params.searchtext = search_text
        search_params.status = cls._anyfy(status)
        search_params.importance = cls._anyfy(importance)
        search_params.assignee = assignee
        search_params.bug_reporter = bug_reporter
        search_params.bug_supervisor = bug_supervisor
        search_params.bug_commenter = bug_commenter
        search_params.subscriber = bug_subscriber
        search_params.owner = owner
        search_params.affected_user = affected_user
        search_params.distribution = distribution
        if has_patch:
            # Import this here to avoid circular imports
            from lp.bugs.interfaces.bugattachment import (
                BugAttachmentType)
            search_params.attachmenttype = BugAttachmentType.PATCH
        search_params.has_cve = has_cve
        if zope_isinstance(tags, (list, tuple)):
            if len(tags) > 0:
                if tags_combinator == BugTagsSearchCombinator.ALL:
                    search_params.tag = all(*tags)
                else:
                    search_params.tag = any(*tags)
        elif zope_isinstance(tags, str):
            search_params.tag = tags
        elif tags is None:
            pass  # tags not supplied
        else:
            raise AssertionError(
                'Tags can only be supplied as a list or a string.')
        search_params.omit_dupes = omit_duplicates
        search_params.omit_targeted = omit_targeted
        if status_upstream is not None:
            if 'pending_bugwatch' in status_upstream:
                search_params.pending_bugwatch_elsewhere = True
            if 'resolved_upstream' in status_upstream:
                search_params.resolved_upstream = True
            if 'open_upstream' in status_upstream:
                search_params.open_upstream = True
            if 'hide_upstream' in status_upstream:
                search_params.has_no_upstream_bugtask = True
        search_params.milestone = cls._anyfy(milestone)
        search_params.component = cls._anyfy(component)
        search_params.sourcepackagename = sourcepackagename
        if has_no_package:
            search_params.sourcepackagename = NULL
        search_params.nominated_for = nominated_for

        search_params.hardware_bus = hardware_bus
        search_params.hardware_vendor_id = hardware_vendor_id
        search_params.hardware_product_id = hardware_product_id
        search_params.hardware_driver_name = hardware_driver_name
        search_params.hardware_driver_package_name = (
            hardware_driver_package_name)
        search_params.hardware_owner_is_bug_reporter = (
            hardware_owner_is_bug_reporter)
        search_params.hardware_owner_is_affected_by_bug = (
            hardware_owner_is_affected_by_bug)
        search_params.hardware_owner_is_subscribed_to_bug = (
            hardware_owner_is_subscribed_to_bug)
        search_params.hardware_is_linked_to_bug = (
            hardware_is_linked_to_bug)
        search_params.linked_branches = linked_branches
        search_params.linked_blueprints = linked_blueprints
        search_params.structural_subscriber = structural_subscriber
        search_params.modified_since = modified_since
        search_params.created_since = created_since

        return search_params


class IBugTaskSet(Interface):
    """A utility to retrieving BugTasks."""
    title = Attribute('Title')

    def get(task_id):
        """Retrieve a BugTask with the given id.

        Raise a NotFoundError if there is no IBugTask
        matching the given id. Raise a zope.security.interfaces.Unauthorized
        if the user doesn't have the permission to view this bug.
        """

    def getBugTasks(bug_ids):
        """Return the bugs with the given IDs and all of its bugtasks.

        :return: A dictionary mapping the bugs to their bugtasks.
        """

    def getBugTaskBadgeProperties(bugtasks):
        """Return whether the bugtasks should have badges.

        Return a mapping from a bug task, to a dict of badge properties.
        """

    def getMultiple(task_ids):
        """Retrieve a dictionary of bug tasks for the given sequence of IDs.

        :param task_ids: a sequence of bug task IDs.

        :return: a dictionary mapping task IDs to tasks. The
            dictionary contains an entry for every bug task ID in
            the given sequence that also matches a bug task in the
            database. The dictionary does not contain entries for
            bug task IDs not present in the database.

        :return: an empty dictionary if the given sequence of IDs
            is empty, or if none of the specified IDs matches a bug
            task in the database.
        """

    def findSimilar(user, summary, product=None, distribution=None,
                    sourcepackagename=None):
        """Find bugs similar to the given summary.

        The search is limited to the given product or distribution
        (together with an optional source package).

        Only BugTasks that the user has access to will be returned.
        """

    def search(params, *args, **kwargs):
        """Search IBugTasks with the given search parameters.

        Note: only use this method of BugTaskSet if you want to query
        tasks across multiple IBugTargets; otherwise, use the
        IBugTarget's searchTasks() method.

        :param search_params: a BugTaskSearchParams object
        :param args: any number of BugTaskSearchParams objects
        :param prejoins: (keyword) A sequence of tuples
            (table, table_join) which should be pre-joined in addition
            to the default prejoins.

        If more than one BugTaskSearchParams is given, return the union of
        IBugTasks which match any of them, with the results ordered by the
        orderby specified in the first BugTaskSearchParams object.
        """

    def searchBugIds(params):
        """Search bug ids.

        This is a variation on IBugTaskSet.search that returns only bug ids.

        :param params: the BugTaskSearchParams to search on.
        """

    def countBugs(user, contexts, group_on):
        """Count open bugs that match params, grouping by group_on.

        This serves results from the bugsummary fact table: it is fast but not
        completely precise. See the bug summary documentation for more detail.

        :param user: The user to query on behalf of.
        :param contexts: A list of contexts to search. Contexts must support
            the IBugSummaryDimension interface.
        :param group_on: The column(s) group on - .e.g (
            BugSummary.distroseries_id, BugSummary.milestone_id) will cause
            grouping by distro series and then milestone.
        :return: A dict {group_instance: count, ...}
        """

    def getStatusCountsForProductSeries(user, product_series):
        """Returns status counts for a product series' bugs.

        Both the nominated and scheduled blueprints are included
        in the count.

        :param product_series: ProductSeries object.
        :return: A list of tuples containing (status_id, count).
        """

    def createTask(bug, owner, target, status=None, importance=None,
                   assignee=None, milestone=None):
        """Create a bug task on a bug and return it.

        If the bug is public, bug supervisors will be automatically
        subscribed.

        If the bug has any accepted series nominations for a supplied
        distribution, series tasks will be created for them.
        """

    def findExpirableBugTasks(min_days_old, user, bug=None, target=None,
                              limit=None):
        """Return a list of bugtasks that are at least min_days_old.

        :param min_days_old: An int representing the minimum days of
            inactivity for a bugtask to be considered expirable. Setting
            this parameter to 0 will return all bugtask that can expire.
        :param user: The `IPerson` doing the search. Only bugs the user
            has permission to view are returned.
        :param bug: An `IBug`. If a bug is provided, only bugtasks that belong
            to the bug may be returned. If bug is None, all bugs are searched.
        :param target: An `IBugTarget`. If a target is provided, only
            bugtasks that belong to the target may be returned. If target
            is None, all bugtargets are searched.
        :param limit: An int for limiting the number of bugtasks returned.
        :return: A ResultSet of bugtasks that are considered expirable.

        A bugtask is expirable if its status is Incomplete, and the bug
        report has been never been confirmed, and it has been inactive for
        min_days_old. Only bugtasks that belong to Products or Distributions
        that use launchpad to track bugs can be returned. The implementation
        must define the criteria for determining that the bug report is
        inactive and have never been confirmed.
        """

    def maintainedBugTasks(person, minimportance=None,
                           showclosed=None, orderby=None, user=None):
        """Return all bug tasks assigned to a package/product maintained by
        :person:.

        By default, closed (FIXCOMMITTED, INVALID) tasks are not
        returned. If you want closed tasks too, just pass
        showclosed=True.

        If minimportance is not None, return only the bug tasks with
        importance greater than minimportance.

        If you want the results ordered, you have to explicitly specify an
        <orderBy>. Otherwise the order used is not predictable.
        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.

        The <user> parameter is necessary to make sure we don't return any
        bugtask of a private bug for which the user is not subscribed. If
        <user> is None, no private bugtasks will be returned.
        """

    def getOrderByColumnDBName(col_name):
        """Get the database name for col_name.

        If the col_name is unrecognized, a KeyError is raised.
        """

    def getBugCountsForPackages(user, packages):
        """Return open bug counts for the list of packages.

        :param user: The user doing the search. Private bugs that this
            user doesn't have access to won't be included in the count.
        :param packages: A list of `IDistributionSourcePackage`
            instances.

        :return: A list of dictionaries, where each dict contains:
            'package': The package the bugs are open on.
            'open': The number of open bugs.
            'open_critical': The number of open critical bugs.
            'open_unassigned': The number of open unassigned bugs.
            'open_inprogress': The number of open bugs that are In Progress.
        """

    def getOpenBugTasksPerProduct(user, products):
        """Return open bugtask count for multiple products."""

    def getPrecachedNonConjoinedBugTasks(user, milestone):
        """List of non-conjoined bugtasks targeted to the milestone.

        The assignee and the assignee's validity are precached.
        """

    def getBugTaskTargetMilestones(bugtasks):
        """Get all the milestones for the selected bugtasks' targets."""

    open_bugtask_search = Attribute("A search returning open bugTasks.")

    def buildUpstreamClause(params):
        """Create a SQL clause to do upstream checks in a bug search.

        :return: A string SQL expression.
        """


def valid_remote_bug_url(value):
    """Verify that the URL is to a bug to a known bug tracker."""
    try:
        getUtility(IBugWatchSet).extractBugTrackerAndBug(value)
    except NoBugTrackerFound:
        pass
    except UnrecognizedBugTrackerURL:
        raise LaunchpadValidationError(
            "Launchpad does not recognize the bug tracker at this URL.")
    return True


class ILinkPackaging(Interface):
    """Form for linking a source package to a project."""
    add_packaging = Bool(
        title=_('Link the package to the upstream project?'),
        description=_('Always suggest this project when adding an '
                      'upstream bug for this package.'),
        required=True, default=False)


class IAddBugTaskForm(ILinkPackaging):
    """Form for adding an upstream bugtask."""
    # It is tempting to replace the first three attributes here with their
    # counterparts from IUpstreamBugTask and IDistroBugTask.
    # BUT: This will cause OOPSes with adapters, hence IAddBugTask reinvents
    # the wheel somewhat. There is a test to ensure that this remains so.
    product = Choice(title=_('Project'), required=True, vocabulary='Product')
    distribution = Choice(
        title=_("Distribution"), required=True, vocabulary='Distribution')
    sourcepackagename = Choice(
        title=_("Source Package Name"), required=False,
        description=_("The source package in which the bug occurs. "
                      "Leave blank if you are not sure."),
        vocabulary='SourcePackageName')
    bug_url = StrippedTextLine(
        title=_('URL'), required=False, constraint=valid_remote_bug_url,
        description=_("The URL of this bug in the remote bug tracker."))


class IAddBugTaskWithProductCreationForm(ILinkPackaging):

    bug_url = StrippedTextLine(
        title=_('Bug URL'), required=True, constraint=valid_remote_bug_url,
        description=_("The URL of this bug in the remote bug tracker."))
    displayname = TextLine(title=_('Project name'))
    name = ProductNameField(
        title=_('Project ID'), constraint=name_validator, required=True,
        description=_(
            "A short name starting with a lowercase letter or number, "
            "followed by letters, dots, hyphens or plusses. e.g. firefox, "
            "linux, gnome-terminal."))
    summary = Summary(title=_('Project summary'), required=True)


class INominationsReviewTableBatchNavigator(ITableBatchNavigator):
    """Marker interface to render custom template for the bug nominations."""


class ICreateQuestionFromBugTaskForm(Interface):
    """Form for creating and question from a bug."""
    comment = Text(
        title=_('Comment'),
        description=_('An explanation of why the bug report is a question.'),
        required=False)


class IRemoveQuestionFromBugTaskForm(Interface):
    """Form for removing a question created from a bug."""
    comment = Text(
        title=_('Comment'),
        description=_('An explanation of why the bug report is valid.'),
        required=False)
