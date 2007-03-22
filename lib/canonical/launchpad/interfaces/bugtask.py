# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Bug task interfaces."""

__metaclass__ = type

__all__ = [
    'BugTaskSearchParams',
    'ConjoinedBugTaskEditError',
    'IBugTask',
    'INullBugTask',
    'IBugTaskSearch',
    'IAddBugTaskForm',
    'IPersonBugTaskSearch',
    'IFrontPageBugTaskSearch',
    'IBugTaskDelta',
    'IUpstreamBugTask',
    'IDistroBugTask',
    'IDistroReleaseBugTask',
    'IProductSeriesBugTask',
    'ISelectResultsSlicable',
    'IBugTaskSet',
    'RESOLVED_BUGTASK_STATUSES',
    'UNRESOLVED_BUGTASK_STATUSES']

from zope.interface import Interface, Attribute
from zope.schema import (
    Bool, Choice, Datetime, Int, Text, TextLine, List, Field)

from sqlos.interfaces import ISelectResults

from canonical.lp import dbschema
from canonical.launchpad import _
from canonical.launchpad.fields import StrippedTextLine, Tag
from canonical.launchpad.interfaces.component import IComponent
from canonical.launchpad.interfaces.launchpad import IHasDateCreated, IHasBug
from canonical.launchpad.interfaces.sourcepackage import ISourcePackage


# XXX: Brad Bollenbach, 2005-12-02: In theory, NEEDSINFO belongs in
# UNRESOLVED_BUGTASK_STATUSES, but the semantics of our current reports would
# break if it were added to the list below. See
# <https://launchpad.net/malone/bugs/5320>
# XXX: matsubara, 2006-02-02: I added the NEEDSINFO as a short-term solution
# to bug https://launchpad.net/products/malone/+bug/4201
UNRESOLVED_BUGTASK_STATUSES = (
    dbschema.BugTaskStatus.UNCONFIRMED,
    dbschema.BugTaskStatus.CONFIRMED,
    dbschema.BugTaskStatus.INPROGRESS,
    dbschema.BugTaskStatus.NEEDSINFO,
    dbschema.BugTaskStatus.FIXCOMMITTED)

RESOLVED_BUGTASK_STATUSES = (
    dbschema.BugTaskStatus.FIXRELEASED,
    dbschema.BugTaskStatus.REJECTED)


class ConjoinedBugTaskEditError(Exception):
    """An error raised when trying to modify a conjoined bugtask."""


class IBugTask(IHasDateCreated, IHasBug):
    """A bug needing fixing in a particular product or package."""

    id = Int(title=_("Bug Task #"))
    bug = Int(title=_("Bug #"))
    product = Choice(title=_('Product'), required=False, vocabulary='Product')
    productseries = Choice(
        title=_('Product Series'), required=False, vocabulary='ProductSeries')
    sourcepackagename = Choice(
        title=_("Package"), required=False,
        vocabulary='SourcePackageName')
    distribution = Choice(
        title=_("Distribution"), required=False, vocabulary='Distribution')
    distrorelease = Choice(
        title=_("Distribution Release"), required=False,
        vocabulary='DistroRelease')
    milestone = Choice(
        title=_('Milestone'), required=False, vocabulary='Milestone')
    # XXX: the status and importance's vocabularies do not
    # contain an UNKNOWN item in bugtasks that aren't linked to a remote
    # bugwatch; this would be better described in a separate interface,
    # but adding a marker interface during initialization is expensive,
    # and adding it post-initialization is not trivial.
    #   -- kiko, 2006-03-23
    status = Choice(
        title=_('Status'), vocabulary='BugTaskStatus',
        default=dbschema.BugTaskStatus.UNCONFIRMED)
    importance = Choice(
        title=_('Importance'), vocabulary='BugTaskImportance',
        default=dbschema.BugTaskImportance.UNDECIDED)
    statusexplanation = Text(
        title=_("Status notes (optional)"), required=False)
    assignee = Choice(
        title=_('Assigned to'), required=False, vocabulary='ValidAssignee')
    bugwatch = Choice(title=_("Remote Bug Details"), required=False,
        vocabulary='BugWatch', description=_("Select the bug watch that "
        "represents this task in the relevant bug tracker. If none of the "
        "bug watches represents this particular bug task, leave it as "
        "(None). Linking the remote bug watch with the task in "
        "this way means that a change in the remote bug status will change "
        "the status of this bug task in Malone."))
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
    target_uses_malone = Bool(title=_("Whether the bugtask's target uses Malone "
                              "officially"))
    targetname = Text(title=_("The short, descriptive name of the target"),
                      readonly=True)
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
    # allows us to compare it to the current value and see if there are any new
    # bugcontacts that should get an email containing full bug details (rather
    # than just the standard change mail.) It is a property on IBugTask because
    # we currently only ever need this value for events handled on IBugTask.
    bug_subscribers = Field(
        title=_("A list of IPersons subscribed to the bug, whether directly or "
        "indirectly."), readonly=True)

    conjoined_master = Attribute(
        "The series- or release-specific bugtask in a conjoined relationship")
    conjoined_slave = Attribute(
        "The generic bugtask in a conjoined relationship")

    def setImportanceFromDebbugs(severity):
        """Set the Malone BugTask importance on the basis of a debbugs
        severity.  This maps from the debbugs severity values ('normal',
        'important', 'critical', 'serious', 'minor', 'wishlist', 'grave') to
        the Malone importance values, and returns the relevant Malone
        importance.
        """

    def transitionToStatus(new_status):
        """Perform a workflow transition to the new_status.

        For certain statuses, e.g. Confirmed, other actions will
        happen, like recording the date when the task enters this
        status.
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


class IBugTaskSearchBase(Interface):
    """The basic search controls."""
    searchtext = TextLine(title=_("Bug ID or text:"), required=False)
    status = List(
        title=_('Status'),
        value_type=IBugTask['status'],
        default=list(UNRESOLVED_BUGTASK_STATUSES),
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
    status_upstream = Choice(
        title=_('Status Upstream'), required=False,
        vocabulary="AdvancedBugTaskUpstreamStatus")
    has_cve = Bool(
        title=_('Show only bugs associated with a CVE'), required=False)
    bug_contact = Choice(
        title=_('Bug contact'), vocabulary='ValidPersonOrTeam', required=False)


class IBugTaskSearch(IBugTaskSearchBase):
    """The schema used by a bug task search form not on a Person.

    Note that this is slightly different than simply IBugTask because
    some of the field types are different (e.g. it makes sense for
    status to be a Choice on a bug task edit form, but it makes sense
    for status to be a List field on a search form, where more than
    one value can be selected.)
    """
    status_upstream = Choice(
        title=_('Status Upstream'), required=False,
        vocabulary="AdvancedBugTaskUpstreamStatus")
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


class IFrontPageBugTaskSearch(IBugTaskSearchBase):

    scope = Choice(
        title=u"Search Scope", required=False,
        vocabulary="DistributionOrProductOrProject")


class IBugTaskDelta(Interface):
    """The change made to a bug task (e.g. in an edit screen).

    If product is not None, the sourcepackagename must be None.

    Likewise, if sourcepackagename is not None, product must be None.
    """
    targetname = Attribute("Where this change exists.")
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
        {'old' : BugTaskImportance.FOO, 'new' : BugTaskImportance.BAR}, or None,
        if no change was made to the importance.
        """)
    assignee = Attribute(
        """The change made to the assignee of this task.

        The value is a dict like {'old' : IPerson, 'new' : IPerson}, or None,
        if no change was made to the assignee.
        """)
    statusexplanation = Attribute("The new value of the status notes.")
    bugwatch = Attribute("The bugwatch which governs this task.")


# XXX, Brad Bollenbach, 2006-08-03: This interface should be
# renamed. See https://launchpad.net/bugs/55089 .
class IUpstreamBugTask(IBugTask):
    """A bug needing fixing in a product."""
    product = Choice(title=_('Product'), required=True, vocabulary='Product')


class IDistroBugTask(IBugTask):
    """A bug needing fixing in a distribution, possibly a specific package."""
    sourcepackagename = Choice(
        title=_("Source Package Name"), required=False,
        description=_("The source package in which the bug occurs. "
        "Leave blank if you are not sure."),
        vocabulary='SourcePackageName')
    distribution = Choice(
        title=_("Distribution"), required=True, vocabulary='Distribution')


class IDistroReleaseBugTask(IBugTask):
    """A bug needing fixing in a distrorealease, possibly a specific package."""
    sourcepackagename = Choice(
        title=_("Source Package Name"), required=True,
        vocabulary='SourcePackageName')
    distrorelease = Choice(
        title=_("Distribution Release"), required=True,
        vocabulary='DistroRelease')


class IProductSeriesBugTask(IBugTask):
    """A bug needing fixing a productseries."""
    productseries = Choice(
        title=_("Product Series"), required=True,
        vocabulary='ProductSeries')


# XXX: Brad Bollenbach, 2005-02-03: This interface should be removed
# when spiv pushes a fix upstream for the bug that makes this hackery
# necessary:
#
#     https://launchpad.ubuntu.com/malone/bugs/121
class ISelectResultsSlicable(ISelectResults):
    def __getslice__(i, j):
        """Called to implement evaluation of self[i:j]."""


class BugTaskSearchParams:
    """Encapsulates search parameters for BugTask.search()

    Details:

      user is an object that provides IPerson, and represents the
      person performing the query (which is important to know for, for
      example, privacy-aware results.) If user is None, the search
      will be filtered to only consider public bugs.

      product, distribution and distrorelease (IBugTargets) should /not/
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
    distrorelease = None
    productseries = None
    def __init__(self, user, bug=None, searchtext=None, status=None,
                 importance=None, milestone=None,
                 assignee=None, sourcepackagename=None, owner=None,
                 statusexplanation=None, attachmenttype=None,
                 orderby=None, omit_dupes=False, subscriber=None,
                 component=None, pending_bugwatch_elsewhere=False,
                 only_resolved_upstream=False, has_no_upstream_bugtask=False,
                 tag=None, has_cve=False, bug_contact=None, bug_reporter=None):
        self.bug = bug
        self.searchtext = searchtext
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
        self.subscriber = subscriber
        self.component = component
        self.pending_bugwatch_elsewhere = pending_bugwatch_elsewhere
        self.only_resolved_upstream = only_resolved_upstream
        self.has_no_upstream_bugtask = has_no_upstream_bugtask
        self.tag = tag
        self.has_cve = has_cve
        self.bug_contact = bug_contact
        self.bug_reporter = bug_reporter

    def setProduct(self, product):
        """Set the upstream context on which to filter the search."""
        self.product = product

    def setProject(self, project):
        """Set the upstream context on which to filter the search."""
        self.project = project

    def setDistribution(self, distribution):
        """Set the distribution context on which to filter the search."""
        self.distribution = distribution

    def setDistributionRelease(self, distrorelease):
        """Set the distrorelease context on which to filter the search."""
        self.distrorelease = distrorelease

    def setProductSeries(self, productseries):
        """Set the productseries context on which to filter the search."""
        self.productseries = productseries

    def setSourcePackage(self, sourcepackage):
        """Set the sourcepackage context on which to filter the search."""
        if ISourcePackage.providedBy(sourcepackage):
            # This is a sourcepackage in a distro release.
            self.distrorelease = sourcepackage.distrorelease
        else:
            # This is a sourcepackage in a distribution.
            self.distribution = sourcepackage.distribution
        self.sourcepackagename = sourcepackage.sourcepackagename


class IBugTaskSet(Interface):

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

    def search(params):
        """Return a set of IBugTasks.

        Note: only use this method of BugTaskSet if you want to query
        tasks across multiple IBugTargets; otherwise, use the
        IBugTarget's searchTasks() method.

        search() returns the tasks that satisfy the query specified in
        the BugTaskSearchParams argument supplied.
        """

    def createTask(bug, product=None, productseries=None, distribution=None,
                   distrorelease=None, sourcepackagename=None, status=None,
                   importance=None, assignee=None, owner=None, milestone=None):
        """Create a bug task on a bug and return it.

        If the bug is public, bug contacts will be automatically
        subscribed.

        If the bug has any accepted release nominations for a supplied
        distribution, release tasks will be created for them.

        Exactly one of product, distribution or distrorelease must be provided.
        """

    def maintainedBugTasks(person, minimportance=None,
                           showclosed=None, orderby=None, user=None):
        """Return all bug tasks assigned to a package/product maintained by
        :person:.

        By default, closed (FIXCOMMITTED, REJECTED) tasks are not
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

    # XXX: get rid of this kludge when we have proper security for
    # scripts   -- kiko, 2006-03-23
    def dangerousGetAllTasks():
        """DO NOT USE THIS METHOD UNLESS YOU KNOW WHAT YOU ARE DOING

        Returns ALL BugTasks. YES, THAT INCLUDES PRIVATE ONES. Do not
        use this method. DO NOT USE IT. I REPEAT: DO NOT USE IT.

        This method exists solely for the purpose of scripts that need
        to do gardening over all bug tasks; the current example is
        update-bugtask-targetnamecaches.
        """

class IAddBugTaskForm(Interface):
    """Form for adding an upstream bugtask."""
    product = IUpstreamBugTask['product']
    distribution = IDistroBugTask['distribution']
    sourcepackagename = IDistroBugTask['sourcepackagename']
    bug_url = StrippedTextLine(
        title=_('URL'), required=False,
        description=_("The URL of this bug in the remote bug tracker."))

