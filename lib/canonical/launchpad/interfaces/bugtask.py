# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Bug task interfaces."""

__metaclass__ = type

__all__ = [
    'BUG_CONTACT_BUGTASK_STATUSES',
    'BugTaskImportance',
    'BugTaskSearchParams',
    'BugTaskStatus',
    'BugTaskStatusSearch',
    'BugTaskStatusSearchDisplay',
    'ConjoinedBugTaskEditError',
    'IAddBugTaskForm',
    'IBugTask',
    'IBugTaskDelta',
    'IBugTaskSearch',
    'IBugTaskSet',
    'IDistroBugTask',
    'IDistroSeriesBugTask',
    'IFrontPageBugTaskSearch',
    'INominationsReviewTableBatchNavigator',
    'INullBugTask',
    'IPersonBugTaskSearch',
    'IProductSeriesBugTask',
    'ISelectResultsSlicable',
    'IUpstreamBugTask',
    'IUpstreamProductBugTaskSearch',
    'RESOLVED_BUGTASK_STATUSES',
    'UNRESOLVED_BUGTASK_STATUSES']

from zope.component import getUtility
from zope.interface import Attribute, Interface
from zope.schema import (
    Bool, Choice, Datetime, Int, Text, TextLine, List, Field)
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from sqlos.interfaces import ISelectResults

from canonical.launchpad import _
from canonical.launchpad.fields import StrippedTextLine, Tag
from canonical.launchpad.interfaces.component import IComponent
from canonical.launchpad.interfaces.launchpad import IHasDateCreated, IHasBug
from canonical.launchpad.interfaces.mentoringoffer import ICanBeMentored
from canonical.launchpad.interfaces.sourcepackage import ISourcePackage
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.webapp.interfaces import ITableBatchNavigator
from canonical.lazr import (
    DBEnumeratedType, DBItem, use_template)


class BugTaskImportance(DBEnumeratedType):
    """Bug Task Importance

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
        system stability, data integrity and / or remote access
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
        should if possible be fixed when next the maintainer does an
        upload. For example, it might be a typo in a document.
        """)

    WISHLIST = DBItem(10, """
        Wishlist

        This is not a bug, but is a request for an enhancement or
        new feature that does not yet exist in the package. It does
        not affect system stability, it might be a usability or
        documentation fix.
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

    INCOMPLETE = DBItem(15, """
        Incomplete

        More info is required before making further progress on this bug, likely
        from the reporter. E.g. the exact error message the user saw, the URL
        the user was visiting when the bug occurred, etc.
        """)

    INVALID = DBItem(17, """
        Invalid

        This is not a bug. It could be a support request, spam, or a misunderstanding.
        """)

    WONTFIX = DBItem(18, """
        Won't Fix

        This will not be fixed. For example, this might be a bug but it's not considered worth
        fixing, or it might not be fixed in this release.
        """)

    CONFIRMED = DBItem(20, """
        Confirmed

        This bug has been reviewed, verified, and confirmed as something needing
        fixing. Anyone can set this status.
        """)

    TRIAGED = DBItem(21, """
        Triaged

        This bug has been reviewed, verified, and confirmed as
        something needing fixing. The user must be a bug contact to
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

    # DBItem values 35 and 40 are used by
    # BugTaskStatusSearch.INCOMPLETE_WITH_RESPONSE and
    # BugTaskStatusSearch.INCOMPLETE_WITHOUT_RESPONSE

    UNKNOWN = DBItem(999, """
        Unknown

        The status of this bug task is unknown.
        """)


class BugTaskStatusSearch(DBEnumeratedType):
    """Bug Task Status

    The various possible states for a bugfix in searches.
    """
    use_template(BugTaskStatus, exclude=('UNKNOWN'))

    sort_order = (
        'NEW', 'INCOMPLETE_WITH_RESPONSE', 'INCOMPLETE_WITHOUT_RESPONSE',
        'INCOMPLETE', 'INVALID', 'WONTFIX', 'CONFIRMED', 'TRIAGED',
        'INPROGRESS', 'FIXCOMMITTED', 'FIXRELEASED')

    INCOMPLETE_WITH_RESPONSE = DBItem(35, """
        Incomplete (with response)

        This bug has new information since it was last marked
        as requiring a response.
        """)

    INCOMPLETE_WITHOUT_RESPONSE = DBItem(40, """
        Incomplete (without response)

        This bug requires more information, but no additional
        details were supplied yet..
        """)

class BugTaskStatusSearchDisplay(DBEnumeratedType):
    """Bug Task Status

    The various possible states for a bugfix in advanced
    bug search forms.
    """
    use_template(BugTaskStatusSearch, exclude=('INCOMPLETE'))


# XXX: Brad Bollenbach 2005-12-02 bugs=5320:
# In theory, INCOMPLETE belongs in UNRESOLVED_BUGTASK_STATUSES, but the
# semantics of our current reports would break if it were added to the
# list below.

# XXX: matsubara 2006-02-02 bug=4201:
# I added the INCOMPLETE as a short-term solution.
UNRESOLVED_BUGTASK_STATUSES = (
    BugTaskStatus.NEW,
    BugTaskStatus.INCOMPLETE,
    BugTaskStatus.CONFIRMED,
    BugTaskStatus.TRIAGED,
    BugTaskStatus.INPROGRESS,
    BugTaskStatus.FIXCOMMITTED)

RESOLVED_BUGTASK_STATUSES = (
    BugTaskStatus.FIXRELEASED,
    BugTaskStatus.INVALID,
    BugTaskStatus.WONTFIX)

BUG_CONTACT_BUGTASK_STATUSES = (
    BugTaskStatus.WONTFIX,
    BugTaskStatus.TRIAGED)

DEFAULT_SEARCH_BUGTASK_STATUSES = (
    BugTaskStatusSearch.NEW,
    BugTaskStatusSearch.INCOMPLETE_WITH_RESPONSE,
    BugTaskStatusSearch.CONFIRMED,
    BugTaskStatusSearch.TRIAGED,
    BugTaskStatusSearch.INPROGRESS,
    BugTaskStatusSearch.FIXCOMMITTED)

class ConjoinedBugTaskEditError(Exception):
    """An error raised when trying to modify a conjoined bugtask."""


class IBugTask(IHasDateCreated, IHasBug, ICanBeMentored):
    """A bug needing fixing in a particular product or package."""

    id = Int(title=_("Bug Task #"))
    bug = Int(title=_("Bug #"))
    product = Choice(title=_('Project'), required=False, vocabulary='Product')
    productseries = Choice(
        title=_('Series'), required=False, vocabulary='ProductSeries')
    sourcepackagename = Choice(
        title=_("Package"), required=False,
        vocabulary='SourcePackageName')
    distribution = Choice(
        title=_("Distribution"), required=False, vocabulary='Distribution')
    distroseries = Choice(
        title=_("Series"), required=False,
        vocabulary='DistroSeries')
    milestone = Choice(
        title=_('Milestone'), required=False, vocabulary='Milestone')
    # XXX kiko 2006-03-23:
    # The status and importance's vocabularies do not
    # contain an UNKNOWN item in bugtasks that aren't linked to a remote
    # bugwatch; this would be better described in a separate interface,
    # but adding a marker interface during initialization is expensive,
    # and adding it post-initialization is not trivial.
    status = Choice(
        title=_('Status'), vocabulary=BugTaskStatus,
        default=BugTaskStatus.NEW)
    importance = Choice(
        title=_('Importance'), vocabulary=BugTaskImportance,
        default=BugTaskImportance.UNDECIDED)
    statusexplanation = Text(
        title=_("Status notes (optional)"), required=False)
    assignee = Choice(
        title=_('Assigned to'), required=False, vocabulary='ValidAssignee')
    bugtargetdisplayname = Text(
        title=_("The short, descriptive name of the target"), readonly=True)
    bugtargetname = Text(
        title=_(
            "The target as presented in mail notifications"), readonly=True)
    bugwatch = Choice(title=_("Remote Bug Details"), required=False,
        vocabulary='BugWatch', description=_("Select the bug watch that "
        "represents this task in the relevant bug tracker. If none of the "
        "bug watches represents this particular bug task, leave it as "
        "(None). Linking the remote bug watch with the task in "
        "this way means that a change in the remote bug status will change "
        "the status of this bug task in Launchpad."))
    date_assigned = Datetime(
        title=_("Date Assigned"),
        description=_("The date on which this task was assigned to someone."))
    datecreated = Datetime(
        title=_("Date Created"),
        description=_("The date on which this task was created."))
    date_confirmed = Datetime(
        title=_("Date Confirmed"),
        description=_("The date on which this task was marked Confirmed."))
    date_inprogress = Datetime(
        title=_("Date In Progress"),
        description=_("The date on which this task was marked In Progress."))
    date_closed = Datetime(
        title=_("Date Closed"),
        description=_(
            "The date on which this task was marked either Fix Committed or "
            "Fix Released."))
    age = Datetime(
        title=_("Age"),
        description=_(
            "The age of this task, expressed as the length of time between "
            "datecreated and now."))
    owner = Int()
    target = Attribute("The software in which this bug should be fixed")
    target_uses_malone = Bool(
        title=_("Whether the bugtask's target uses Launchpad officially"))
    title = Text(title=_("The title of the bug related to this bugtask"),
                         readonly=True)
    related_tasks = Attribute("IBugTasks related to this one, namely other "
                              "IBugTasks on the same IBug.")
    pillar = Attribute(
        "The LP pillar (product or distribution) associated with this "
        "task.")
    other_affected_pillars = Attribute(
        "The other pillars (products or distributions) affected by this bug. "
        "This returns a list of pillars OTHER THAN the pillar associated "
        "with this particular bug.")
    # This property does various database queries. It is a property so a
    # "snapshot" of its value will be taken when a bugtask is modified, which
    # allows us to compare it to the current value and see if there are any
    # new bugcontacts that should get an email containing full bug details
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

    is_complete = Attribute(
        "True or False depending on whether or not there is more work "
        "required on this bug task.")

    def subscribe(person):
        """Subscribe this person to the underlying bug.

        This method is required here so that MentorshipOffers can happen on
        IBugTask. When we move to context-less bug presentation (where the
        bug is at /bugs/n?task=ubuntu) then we can eliminate this if it is
        no longer useful.
        """

    def isSubscribed(person):
        """Return True if the person is an explicit subscriber to the
        underlying bug for this bugtask.

        This method is required here so that MentorshipOffers can happen on
        IBugTask. When we move to context-less bug presentation (where the
        bug is at /bugs/n?task=ubuntu) then we can eliminate this if it is
        no longer useful.
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
        be a bug contact or the owner of the project.
        """

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

    def transitionToAssignee(assignee):
        """Perform a workflow transition to the given assignee.

        When the bugtask assignee is changed from None to an IPerson
        object, the date_assigned is set on the task. If the assignee
        value is set to None, date_assigned is also set to None.
        """

    def updateTargetNameCache():
        """Update the targetnamecache field in the database.

        This method is meant to be called when an IBugTask is created or
        modified and will also be called from the update_stats.py cron script
        to ensure that the targetnamecache is properly updated when, for
        example, an IDistribution is renamed.
        """

    def asEmailHeaderValue():
        """Return a value suitable for an email header value for this bugtask.

        The return value is a single line of arbitrary length, so header folding
        should be done by the callsite, as needed.

        For an upstream task, this value might look like:

          product=firefox; status=New; importance=Critical; assignee=None;

        See doc/bugmail-headers.txt for a complete explanation and more
        examples.
        """

    def getDelta(old_task):
        """Compute the delta from old_task to this task.

        old_task and this task are either both IDistroBugTask's or both
        IUpstreamBugTask's, otherwise a TypeError is raised.

        Returns an IBugTaskDelta or None if there were no changes between
        old_task and this task.
        """


class INullBugTask(IBugTask):
    """A marker interface for an IBugTask that doesn't exist in a context.

    An INullBugTask is useful when wanting to view a bug in a context
    where that bug hasn't yet been reported. This might happen, for
    example, when searching to see if a bug you want to report has
    already been filed and finding matching reports that don't yet
    have tasks reported in your context.
    """

PENDING_BUGWATCH_VOCABUARY = SimpleVocabulary(
    [SimpleTerm(
        "pending_bugwatch",
        title="Show only bugs that need to be forwarded to an upstream bug "
              "tracker")])

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

class IBugTaskSearchBase(Interface):
    """The basic search controls."""
    searchtext = TextLine(title=_("Bug ID or text:"), required=False)
    status = List(
        title=_('Status'),
        value_type=Choice(title=_('Status'), vocabulary=BugTaskStatusSearch, default=BugTaskStatusSearch.NEW),
        default=list(DEFAULT_SEARCH_BUGTASK_STATUSES),
        required=False)
    importance = List(
        title=_('Importance'),
        value_type=IBugTask['importance'],
        required=False)
    assignee = Choice(
        title=_('Assignee'), vocabulary='ValidAssignee', required=False)
    bug_reporter = Choice(
        title=_('Bug Reporter'), vocabulary='ValidAssignee', required=False)
    omit_dupes = Bool(
        title=_('Omit duplicate bugs'), required=False,
        default=True)
    omit_targeted = Bool(
        title=_('Omit bugs targeted to series'), required=False,
        default=True)
    statusexplanation = TextLine(
        title=_("Status notes"), required=False)
    has_patch = Bool(
        title=_('Show only bugs with patches available'), required=False,
        default=False)
    has_no_package = Bool(
        title=_('Exclude bugs with packages specified'),
        required=False, default=False)
    milestone_assignment = Choice(
        title=_('Target'), vocabulary="Milestone", required=False)
    milestone = List(
        title=_('Target'), value_type=IBugTask['milestone'], required=False)
    component = List(
        title=_('Component'), value_type=IComponent['name'], required=False)
    tag = List(title=_("Tag"), value_type=Tag(), required=False)
    status_upstream = List(
        title=_('Status Upstream'),
        value_type=Choice(vocabulary=UPSTREAM_STATUS_VOCABULARY),
        required=False)
    has_cve = Bool(
        title=_('Show only bugs associated with a CVE'), required=False)
    bug_contact = Choice(
        title=_('Bug contact'), vocabulary='ValidPersonOrTeam',
        required=False)
    bug_commenter = Choice(
        title=_('Bug commenter'), vocabulary='ValidPersonOrTeam',
        required=False)
    subscriber = Choice(
        title=_('Bug subscriber'), vocabulary='ValidPersonOrTeam',
        required=False)


class IBugTaskSearch(IBugTaskSearchBase):
    """The schema used by a bug task search form not on a Person.

    Note that this is slightly different than simply IBugTask because
    some of the field types are different (e.g. it makes sense for
    status to be a Choice on a bug task edit form, but it makes sense
    for status to be a List field on a search form, where more than
    one value can be selected.)
    """
    tag = List(
        title=_("Tags"), description=_("Separated by whitespace."),
        value_type=Tag(), required=False)


class IPersonBugTaskSearch(IBugTaskSearchBase):
    """The schema used by the bug task search form of a person."""
    sourcepackagename = Choice(
        title=_("Source Package Name"), required=False,
        description=_("The source package in which the bug occurs. "
        "Leave blank if you are not sure."),
        vocabulary='SourcePackageName')
    distribution = Choice(
        title=_("Distribution"), required=False, vocabulary='Distribution')


class IUpstreamProductBugTaskSearch(IBugTaskSearch):
    """The schema used by the bug task search form for upstream products.
    
    This schema is the same as IBugTaskSearch, except that it has only
    one choice for Status Upstream.
    """
    status_upstream = List(
        title=_('Status Upstream'),
        value_type=Choice(vocabulary=PENDING_BUGWATCH_VOCABUARY),
        required=False)


class IFrontPageBugTaskSearch(IBugTaskSearchBase):
    """Additional search options for the front page of bugs."""
    scope = Choice(
        title=u"Search Scope", required=False,
        vocabulary="DistributionOrProductOrProject")


class IBugTaskDelta(Interface):
    """The change made to a bug task (e.g. in an edit screen).

    If product is not None, the sourcepackagename must be None.

    Likewise, if sourcepackagename is not None, product must be None.
    """
    targetname = Attribute("Where this change exists.")
    bugtargetname = Attribute("Near-unique ID of where the change exists.")
    bugtask = Attribute("The modified IBugTask.")
    product = Attribute(
        """The change made to the IProduct of this task.

        The value is a dict like {'old' : IProduct, 'new' : IProduct},
        or None, if no product change was made.
        """)
    sourcepackagename = Attribute(
        """The change made to the ISourcePackageName of this task.

        The value is a dict with the keys
        {'old' : ISourcePackageName, 'new' : ISourcePackageName},
        or None, if no change was made to the sourcepackagename.
        """)
    target = Attribute(
        """The change made to the IMilestone for this task.

        The value is a dict like {'old' : IMilestone, 'new' : IMilestone},
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
    statusexplanation = Attribute("The new value of the status notes.")
    bugwatch = Attribute("The bugwatch which governs this task.")


# XXX Brad Bollenbach 2006-08-03 bugs=55089:
# This interface should be renamed.
class IUpstreamBugTask(IBugTask):
    """A bug needing fixing in a product."""
    product = Choice(title=_('Project'), required=True, vocabulary='Product')


class IDistroBugTask(IBugTask):
    """A bug needing fixing in a distribution, possibly a specific package."""
    sourcepackagename = Choice(
        title=_("Source Package Name"), required=False,
        description=_("The source package in which the bug occurs. "
        "Leave blank if you are not sure."),
        vocabulary='SourcePackageName')
    distribution = Choice(
        title=_("Distribution"), required=True, vocabulary='Distribution')


class IDistroSeriesBugTask(IBugTask):
    """A bug needing fixing in a distrorealease, or a specific package."""
    sourcepackagename = Choice(
        title=_("Source Package Name"), required=True,
        vocabulary='SourcePackageName')
    distroseries = Choice(
        title=_("Series"), required=True,
        vocabulary='DistroSeries')


class IProductSeriesBugTask(IBugTask):
    """A bug needing fixing a productseries."""
    productseries = Choice(
        title=_("Series"), required=True,
        vocabulary='ProductSeries')


# XXX: Brad Bollenbach 2005-02-03 bugs=121:
# This interface should be removed when spiv pushes a fix upstream for
# the bug that makes this hackery necessary.
class ISelectResultsSlicable(ISelectResults):
    """ISelectResults (from SQLOS) should be specifying __getslice__.
    
    This interface defines the missing __getslice__ method.
    """
    def __getslice__(i, j):
        """Called to implement evaluation of self[i:j]."""


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

        lib/canonical/launchpad/doc/bugtask.txt
    """

    product = None
    project = None
    distribution = None
    distroseries = None
    productseries = None
    def __init__(self, user, bug=None, searchtext=None, fast_searchtext=None,
                 status=None, importance=None, milestone=None,
                 assignee=None, sourcepackagename=None, owner=None,
                 statusexplanation=None, attachmenttype=None,
                 orderby=None, omit_dupes=False, subscriber=None,
                 component=None, pending_bugwatch_elsewhere=False,
                 resolved_upstream=False, open_upstream=False,
                 has_no_upstream_bugtask=False, tag=None, has_cve=False,
                 bug_contact=None, bug_reporter=None, nominated_for=None,
                 bug_commenter=None, omit_targeted=False):
        self.bug = bug
        self.searchtext = searchtext
        self.fast_searchtext = fast_searchtext
        self.status = status
        self.importance = importance
        self.milestone = milestone
        self.assignee = assignee
        self.sourcepackagename = sourcepackagename
        self.owner = owner
        self.statusexplanation = statusexplanation
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
        self.bug_contact = bug_contact
        self.bug_reporter = bug_reporter
        self.nominated_for = nominated_for
        self.bug_commenter = bug_commenter

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
        if ISourcePackage.providedBy(sourcepackage):
            # This is a sourcepackage in a distro series.
            self.distroseries = sourcepackage.distroseries
        else:
            # This is a sourcepackage in a distribution.
            self.distribution = sourcepackage.distribution
        self.sourcepackagename = sourcepackage.sourcepackagename


class IBugTaskSet(Interface):
    """A utility to retrieving BugTasks."""
    title = Attribute('Title')

    def get(task_id):
        """Retrieve a BugTask with the given id.

        Raise a NotFoundError if there is no IBugTask
        matching the given id. Raise a zope.security.interfaces.Unauthorized
        if the user doesn't have the permission to view this bug.
        """

    def findSimilar(user, summary, product=None, distribution=None,
                    sourcepackagename=None):
        """Find bugs similar to the given summary.

        The search is limited to the given product or distribution
        (together with an optional source package).

        Only BugTasks that the user has access to will be returned.
        """

    def search(params, *args):
        """Search IBugTasks with the given search parameters.

        Note: only use this method of BugTaskSet if you want to query
        tasks across multiple IBugTargets; otherwise, use the
        IBugTarget's searchTasks() method.

        :search_params: a BugTaskSearchParams object
        :args: any number of BugTaskSearchParams objects

        If more than one BugTaskSearchParams is given, return the union of
        IBugTasks which match any of them, with the results ordered by the
        orderby specified in the first BugTaskSearchParams object.
        """

    def createTask(bug, product=None, productseries=None, distribution=None,
                   distroseries=None, sourcepackagename=None, status=None,
                   importance=None, assignee=None, owner=None,
                   milestone=None):
        """Create a bug task on a bug and return it.

        If the bug is public, bug contacts will be automatically
        subscribed.

        If the bug has any accepted series nominations for a supplied
        distribution, series tasks will be created for them.

        Exactly one of product, distribution or distroseries must be provided.
        """

    def findExpirableBugTasks(min_days_old):
        """Return a list of bugtasks that are at least min_days_old.
        
        An Expirable bug task is unassigned, in the INCOMPLETE status,
        and belongs to a Product or Distribtion that uses Malone.
        """

    def maintainedBugTasks(person, minimportance=None,
                           showclosed=None, orderby=None, user=None):
        """Return all bug tasks assigned to a package/product maintained by
        :person:.

        By default, closed (FIXCOMMITTED, INVALID) tasks are not
        returned. If you want closed tasks too, just pass
        showclosed=True.

        If minimportance is not None, return only the bug tasks with importance
        greater than minimportance.

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

    # XXX kiko 2006-03-23:
    # get rid of this kludge when we have proper security for scripts.
    def dangerousGetAllTasks():
        """DO NOT USE THIS METHOD UNLESS YOU KNOW WHAT YOU ARE DOING

        Returns ALL BugTasks. YES, THAT INCLUDES PRIVATE ONES. Do not
        use this method. DO NOT USE IT. I REPEAT: DO NOT USE IT.

        This method exists solely for the purpose of scripts that need
        to do gardening over all bug tasks; the current example is
        update-bugtask-targetnamecaches.
        """


def valid_remote_bug_url(value):
    from canonical.launchpad.interfaces.bugwatch import (
        IBugWatchSet, NoBugTrackerFound, UnrecognizedBugTrackerURL)
    try:
        tracker, bug = getUtility(IBugWatchSet).extractBugTrackerAndBug(value)
    except NoBugTrackerFound:
        pass
    except UnrecognizedBugTrackerURL:
        raise LaunchpadValidationError(
            "Launchpad does not recognize the bug tracker at this URL.")
    return True


class IAddBugTaskForm(Interface):
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
    visited_steps = TextLine(
        title=_('Visited steps'), required=False,
        description=_("Used to keep track of the steps we visited in a "
                      "wizard-like form."))


class INominationsReviewTableBatchNavigator(ITableBatchNavigator):
    """Marker interface to render custom template for the bug nominations."""
