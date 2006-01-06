# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Bug task interfaces."""

__metaclass__ = type

__all__ = [
    'IBugTask',
    'INullBugTask',
    'IBugTaskSearch',
    'IUpstreamBugTaskSearch',
    'IDistroBugTaskSearch',
    'IPersonBugTaskSearch',
    'IBugTaskDelta',
    'IUpstreamBugTask',
    'IDistroBugTask',
    'IDistroReleaseBugTask',
    'ISelectResultsSlicable',
    'IBugTaskSet',
    'BugTaskSearchParams',
    'UNRESOLVED_BUGTASK_STATUSES',
    'RESOLVED_BUGTASK_STATUSES']

from zope.i18nmessageid import MessageIDFactory
from zope.interface import Interface, Attribute
from zope.schema import (
    Bool, Choice, Datetime, Int, Text, TextLine, List)

from sqlos.interfaces import ISelectResults

from canonical.lp import dbschema
from canonical.launchpad.interfaces.bugattachment import IBugAttachment
from canonical.launchpad.interfaces.launchpad import IHasDateCreated
from canonical.launchpad.interfaces.sourcepackage import ISourcePackage

_ = MessageIDFactory('launchpad')

# XXX: Brad Bollenbach, 2005-12-02: In theory, NEEDSINFO belongs in
# UNRESOLVED_BUGTASK_STATUSES, but the semantics of our current reports would
# break if it were added to the list below. See
# <https://launchpad.net/malone/bugs/5320>
UNRESOLVED_BUGTASK_STATUSES = (
    dbschema.BugTaskStatus.UNCONFIRMED,
    dbschema.BugTaskStatus.CONFIRMED,
    dbschema.BugTaskStatus.INPROGRESS)

RESOLVED_BUGTASK_STATUSES = (
    dbschema.BugTaskStatus.FIXCOMMITTED,
    dbschema.BugTaskStatus.FIXRELEASED,
    dbschema.BugTaskStatus.REJECTED)


class IBugTask(IHasDateCreated):
    """A description of a bug needing fixing in a particular product
    or package."""
    id = Int(title=_("Bug Task #"))
    bug = Int(title=_("Bug #"))
    product = Choice(title=_('Product'), required=False, vocabulary='Product')
    sourcepackagename = Choice(
        title=_("Source Package Name"), required=False,
        vocabulary='SourcePackageName')
    distribution = Choice(
        title=_("Distribution"), required=False, vocabulary='Distribution')
    distrorelease = Choice(
        title=_("Distribution Release"), required=False,
        vocabulary='DistroRelease')
    milestone = Choice(
        title=_('Milestone'), required=False, vocabulary='Milestone')
    status = Choice(
        title=_('Status'), vocabulary='BugTaskStatus',
        default=dbschema.BugTaskStatus.UNCONFIRMED)
    statusexplanation = Text(
        title=_("Status notes (optional)"), required=False)
    priority = Choice(
        title=_('Priority'), vocabulary='BugTaskPriority', required=False)
    severity = Choice(
        title=_('Severity'), vocabulary='BugTaskSeverity',
        default=dbschema.BugTaskSeverity.NORMAL)
    assignee = Choice(
        title=_('Assigned to:'), required=False, vocabulary='ValidAssignee')
    binarypackagename = Choice(
        title=_('Binary PackageName'), required=False,
        vocabulary='BinaryPackageName')
    bugwatch = Choice(title=_("Remote Bug Details"), required=False,
        vocabulary='BugWatch', description=_("Select the bug watch that "
        "represents this task in the relevant bug tracker. If none of the "
        "bug watches represents this particular bug task, leave it as "
        "(None). Linking the remote bug watch with the task in "
        "this way means that a change in the remote bug status will change "
        "the status of this bug task in Malone."))
    dateassigned = Datetime(
        title=_("Date Assigned"),
        description=_("The date on which this task was assigned to someone."))
    datecreated = Datetime(
        title=_("Date Created"),
        description=_("The date on which this task was created."))
    age = Datetime(
        title=_("Age"),
        description=_(
            "The age of this task, expressed as the length of time between "
            "datecreated and now."))
    owner = Int()
    maintainer = TextLine(
        title=_("Maintainer"), required=True, readonly=True)
    maintainer_displayname = TextLine(
        title=_("Maintainer"), required=True, readonly=True)
    target = Attribute("The software in which this bug should be fixed")
    targetname = Attribute("The short, descriptive name of the target")
    title = Attribute("The title of the bug related to this bugtask")
    related_tasks = Attribute("IBugTasks related to this one, namely other "
                              "IBugTasks on the same IBug.")
    statusdisplayhtml = Attribute(
        "A HTML representation of the status. This field produces "
        "its value from the status, assignee and milestone values.")
    statuselsewhere = Attribute(
        "A human-readable representation of the status of this IBugTask's bug "
        "in the other contexts in which it's reported.")

    def setStatusFromDebbugs(status):
        """Set the Malone BugTask status on the basis of a debbugs status.
        This maps from the debbugs status values ('done', 'open',
        'forwarded') to the Malone status values, and returns the relevant
        Malone status.
        """

    def setSeverityFromDebbugs(severity):
        """Set the Malone BugTask severity on the basis of a debbugs
        severity.  This maps from the debbugs severity values ('normal',
        'important', 'critical', 'serious', 'minor', 'wishlist', 'grave') to
        the Malone severity values, and returns the relevant Malone
        severity.
        """

    def updateTargetNameCache(self):
        """Update the targetnamecache field in the database.

        This method is meant to be called when an IBugTask is created or
        modified and will also be called from the update_stats.py cron script
        to ensure that the targetnamecache is properly updated when, for
        example, an IDistribution is renamed.
        """

    def asEmailHeaderValue(self):
        """Return a value suitable for an email header value for this bugtask.

        The return value is a single line of arbitrary length, so header folding
        should be done by the callsite, as needed.

        For an upstream task, this value might look like:

          product=firefox; status=New; priority=None; assignee=None;

        See doc/bugmail-headers.txt for a complete explanation and more
        examples.
        """


class INullBugTask(IBugTask):
    """A marker interface for an IBugTask that doesn't exist in a context.

    An INullBugTask is useful when wanting to view a bug in a context
    where that bug hasn't yet been reported. This might happen, for
    example, when searching to see if a bug you want to report has
    already been filed and finding matching reports that don't yet
    have tasks reported in your context.
    """


class IBugTaskSearch(Interface):
    """The schema used by a bug task search form.

    Note that this is slightly different than simply IBugTask because
    some of the field types are different (e.g. it makes sense for
    status to be a Choice on a bug task edit form, but it makes sense
    for status to be a List field on a search form, where more than
    one value can be selected.)
    """
    searchtext = TextLine(title=_("Bug ID or text:"), required=False)
    status = List(
        title=_('Status:'),
        value_type=IBugTask['status'],
        default=list(UNRESOLVED_BUGTASK_STATUSES),
        required=False)
    severity = List(
        title=_('Severity:'),
        value_type=IBugTask['severity'],
        required=False)
    assignee = Choice(
        title=_('Assignee:'), vocabulary='ValidAssignee', required=False)
    unassigned = Bool(title=_('Unassigned bugs only'), required=False)
    include_dupes = Bool(title=_('Include duplicate bugs'), required=False)
    statusexplanation = TextLine(
        title=_("Status notes:"), required=False)
    attachmenttype = List(
        title=_('Attachment:'),
        value_type=IBugAttachment['type'],
        required=False)


class IUpstreamBugTaskSearch(IBugTaskSearch):
    """The schema used by the bug task search form of a product."""
    milestone_assignment = Choice(
        title=_('Target'), vocabulary="Milestone", required=False)
    milestone = List(
        title=_('Target:'), value_type=IBugTask['milestone'], required=False)


class IDistroBugTaskSearch(IBugTaskSearch):
    """The schema used by the bug task search form of a distribution or
    distribution release."""


class IPersonBugTaskSearch(IBugTaskSearch):
    """The schema used by the bug task search form of a person."""


class IBugTaskDelta(Interface):
    """The change made to a bug task (e.g. in an edit screen).

    If product is not None, both sourcepackagename and binarypackagename must
    be None.

    Likewise, if sourcepackagename and/or binarypackagename is not
    None, product must be None.
    """
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
    binarypackagename = Attribute(
        """The change made to the IBinaryPackageName of this task.

        The value is a dict like
        {'old' : IBinaryPackageName, 'new' : IBinaryPackageName},
        or None, if no change was made to the binarypackagename.
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
    priority = Attribute(
        """The change made to the priority for this task.

        The value is a dict like
        {'old' : BugTaskPriority.FOO, 'new' : BugTaskPriority.BAR}, or None,
        if no change was made to the priority.
        """)
    severity = Attribute(
        """The change made to the severity of this task.

        The value is a dict like
        {'old' : BugTaskSeverity.FOO, 'new' : BugTaskSeverity.BAR}, or None,
        if no change was made to the severity.
        """)
    assignee = Attribute(
        """The change made to the assignee of this task.

        The value is a dict like {'old' : IPerson, 'new' : IPerson}, or None,
        if no change was made to the assignee.
        """)
    statusexplanation = Attribute("The new value of the status notes.")


class IUpstreamBugTask(IBugTask):
    """A description of a bug needing fixing in a particular product."""
    product = Choice(title=_('Product'), required=True, vocabulary='Product')


class IDistroBugTask(IBugTask):
    """A description of a bug needing fixing in a particular package."""
    sourcepackagename = Choice(
        title=_("Source Package Name"), required=False,
        description=_("The source package in which the bug occurs. "
        "Leave blank if you are not sure."),
        vocabulary='SourcePackageName')
    binarypackagename = Choice(
        title=_('Binary PackageName'), required=False,
        vocabulary='BinaryPackageName')
    distribution = Choice(
        title=_("Distribution"), required=True, vocabulary='Distribution')


class IDistroReleaseBugTask(IBugTask):
    """A description of a bug needing fixing in a particular realease."""
    sourcepackagename = Choice(
        title=_("Source Package Name"), required=True,
        vocabulary='SourcePackageName')
    binarypackagename = Choice(
        title=_('Binary PackageName'), required=False,
        vocabulary='BinaryPackageName')
    distrorelease = Choice(
        title=_("Distribution Release"), required=True,
        vocabulary='DistroRelease')


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
    distribution = None
    distrorelease = None
    def __init__(self, user, bug=None, searchtext=None, status=None,
                 priority=None, severity=None, milestone=None,
                 assignee=None, sourcepackagename=None,
                 binarypackagename=None, owner=None,
                 statusexplanation=None, attachmenttype=None,
                 orderby=None, omit_dupes=False, subscriber=None):
        self.bug = bug
        self.searchtext = searchtext
        self.status = status
        self.priority = priority
        self.severity = severity
        self.milestone = milestone
        self.assignee = assignee
        self.sourcepackagename = sourcepackagename
        self.binarypackagename = binarypackagename
        self.owner = owner
        self.statusexplanation = statusexplanation
        self.attachmenttype = attachmenttype
        self.user = user
        self.orderby = orderby
        self.omit_dupes = omit_dupes
        self.subscriber = subscriber

        self._has_context = False

    def setProduct(self, product):
        """Set the upstream context on which to filter the search."""
        assert not self._has_context
        self.product = product
        self._has_context = True

    def setDistribution(self, distribution):
        """Set the distribution context on which to filter the search."""
        assert not self._has_context
        self.distribution = distribution
        self._has_context = True

    def setDistributionRelease(self, distrorelease):
        """Set the distrorelease context on which to filter the search."""
        assert not self._has_context
        self.distrorelease = distrorelease
        self._has_context = True

    def setSourcePackage(self, sourcepackage):
        """Set the sourcepackage context on which to filter the search."""
        assert not self._has_context
        if ISourcePackage.providedBy(sourcepackage):
            # This is a sourcepackage in a distro release.
            self.distrorelease = sourcepackage.distrorelease
        else:
            # This is a sourcepackage in a distribution.
            self.distribution = sourcepackage.distribution
        self.sourcepackagename = sourcepackage.sourcepackagename
        self._has_context = True


class IBugTaskSet(Interface):

    title = Attribute('Title')

    def __getitem__(task_id):
        """Get an IBugTask."""

    def __iter__():
        """Iterate through IBugTasks for a given bug."""

    def get(task_id):
        """Retrieve a BugTask with the given id.

        Raise a zope.exceptions.NotFoundError if there is no IBugTask
        matching the given id. Raise a zope.security.interfaces.Unauthorized
        if the user doesn't have the permission to view this bug.
        """

    def search(params):
        """Return a set of IBugTasks.

        Note: only use this method of BugTaskSet if you want to query
        tasks across multiple IBugTargets; otherwise, use the
        IBugTarget's searchTasks() method.
        
        search() returns the tasks that satisfy the query specified in
        the BugTaskSearchParams argument supplied.
        """

    def createTask(bug, product=None, distribution=None, distrorelease=None,
                   sourcepackagename=None, binarypackagename=None, status=None,
                   priority=None, severity=None, assignee=None, owner=None,
                   milestone=None):
        """Create a bug task on a bug and return it.

        Exactly one of product, distribution or distrorelease must be provided.
        """

    def maintainedBugTasks(person, minseverity=None, minpriority=None,
                           showclosed=None, orderby=None, user=None):
        """Return all bug tasks assigned to a package/product maintained by
        :person:.

        By default, closed (FIXCOMMITTED, REJECTED) tasks are not
        returned. If you want closed tasks too, just pass
        showclosed=True.

        If minseverity is not None, return only the bug tasks with severity 
        greater than minseverity. The same is valid for minpriority/priority.

        If you want the results ordered, you have to explicitly specify an
        <orderBy>. Otherwise the order used is not predictable.
        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.

        The <user> parameter is necessary to make sure we don't return any
        bugtask of a private bug for which the user is not subscribed. If
        <user> is None, no private bugtasks will be returned.
        """

