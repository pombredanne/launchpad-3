from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')
from zope.interface import Interface, Attribute
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.app.form.browser.interfaces import IAddFormCustomization

from sqlos.interfaces import ISelectResults

from canonical.lp import dbschema
from canonical.launchpad.interfaces import IHasProductAndAssignee, \
    IHasDateCreated

class IEditableUpstreamBugTask(IHasProductAndAssignee):
    """A bug assigned to upstream, which is editable by the current
    user."""
    title = Attribute('Title')

class IReadOnlyUpstreamBugTask(IHasProductAndAssignee):
    """A bug assigned to upstream, which is read-only by the current
    user."""
    title = Attribute('Title')

class IEditableDistroBugTask(Interface):
    """A bug assigned to a distro package, which is editable by
    the current user."""
    title = Attribute('Title')

class IReadOnlyDistroBugTask(Interface):
    """A bug assigned to a distro package, which is read-only by the
    current user."""
    title = Attribute('Title')

class IBugTask(IHasDateCreated):
    """A description of a bug needing fixing in a particular product
    or package."""
    id = Int(title=_("Bug Task #"))
    bug = Int(title=_("Bug #"))
    product = Choice(title=_('Product'), required=False, vocabulary='Product')
    sourcepackagename = Choice(
        title=_("Source Package Name"), required=False, vocabulary='SourcePackageName')
    distribution = Choice(
        title=_("Distribution"), required=False, vocabulary='Distribution')
    distrorelease = Choice(
        title=_("Distribution Release"), required=False, vocabulary='DistroRelease')
    milestone = Choice(
        title=_('Target'), required=False, vocabulary='Milestone')
    status = Choice(
        title=_('Bug Status'), vocabulary='BugStatus',
        default=dbschema.BugTaskStatus.NEW)
    priority = Choice(
        title=_('Priority'), vocabulary='BugPriority',
        default=int(dbschema.BugPriority.MEDIUM))
    severity = Choice(
        title=_('Severity'), vocabulary='BugSeverity',
        default=int(dbschema.BugSeverity.NORMAL))
    assignee = Choice(
        title=_('Assignee'), required=False, vocabulary='ValidPerson')
    binarypackagename = Choice(
            title=_('Binary PackageName'), required=False,
            vocabulary='BinaryPackageName'
            )
    dateassigned = Datetime()
    datecreated  = Datetime()
    owner = Int() 
    maintainer = TextLine(
        title=_("Maintainer"), required=True, readonly=True)
    bugtitle = TextLine(
        title=_("Bug Title"), required=True, readonly=True)
    bugdescription = Text(
        title=_("Bug Description"), required=False, readonly=True)

    # used for the page layout
    title = Attribute("Title")

# XXX: Brad Bollenbach, 2005-02-03: This interface should be removed
# when spiv pushes a fix upstream for the bug that makes this hackery
# necessary:
#
#     https://launchpad.ubuntu.com/malone/bugs/121
class ISelectResultsSlicable(ISelectResults):
    def __getslice__(i, j):
        """Called to implement evaluation of self[i:j]."""

class IBugTaskSet(Interface):

    title = Attribute('Title')

    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get an IBugTask."""

    def __iter__():
        """Iterate through IBugTasks for a given bug."""

    def get(id):
        """Retrieve a BugTask with the given id.

        Raise a zope.exceptions.NotFoundError if there is no IBugTask
        matching the given id. Raise a zope.security.interfaces.Unauthorized
        if the user doesn't have the permission to view this bug.
        """

    def search(bug=None, searchtext=None, status=None, priority=None,
               severity=None, product=None, milestone=None, assignee=None,
               submitter=None, orderby=None):
        """Return a set of IBugTasks that satisfy the query arguments.

        Keyword arguments should always be used. The argument passing
        semantics are as follows:

        * BugTaskSet.search(arg = 'foo'): Match all IBugTasks where 
          IBugTask.arg == 'foo'.

        * BugTaskSet.search(arg = any('foo', 'bar')): Match all IBugTasks
          where IBugTask.arg == 'foo' or IBugTask.arg == 'bar'

        * BugTaskSet.search(arg1 = 'foo', arg2 = 'bar'): Match all
          IBugTasks where IBugTask.arg1 == 'foo' and
          IBugTask.arg2 == 'bar'

        For a more thorough treatment, check out:

            lib/canonical/launchpad/doc/bugtask.txt
        """

    def createTask(bug, product=None, distribution=None, distrorelease=None,
                   sourcepackagename=None, binarypackagename=None, status=None,
                   priority=None, severity=None, assignee=None, owner=None,
                   milestone=None):
        """Create a bug task on a bug.

        Exactly one of product, distribution or distrorelease must be provided.
        """

class IBugTasksReport(Interface):

    user = Attribute(_("The user for whom this report will be generated"))

    minseverity = Attribute(_(
        "The minimum severity of tasks to display in this report."))

    minpriority = Attribute(_(
        "The minimum priority of bug fixing tasks to display in this "
        "report."))

    showclosed = Attribute(_(
        "Whether or not to show closed bugs on this report."))

    def maintainedPackageBugs():
        """Return an iterator over the tasks of bugs on distro
        packages the user maintains."""

    def maintainedProductBugs():
        """Return an iterator over the tasks of bugs on upstream
        products the user maintains."""

    def productAssigneeBugs():
        """Return an iterator over the bugtasks on upstream products
        which are assigned directly to the user."""

    def packageAssigneeBugs():
        """Return an iterator over the bug tasks on distro packages
        which are assigned directly to the user."""

    def assignedBugs():
        """An iterator over ALL the bugs directly or indirectly assigned
        to the person."""
