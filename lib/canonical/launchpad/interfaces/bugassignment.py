
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')
from zope.interface import Interface, Attribute

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.app.form.browser.interfaces import IAddFormCustomization

from canonical.lp import dbschema
from canonical.launchpad.interfaces import IHasProductAndAssignee

class IEditableUpstreamBugTask(IHasProductAndAssignee):
    """A bug assigned to upstream, which is editable by the current
    user."""
    pass

class IReadOnlyUpstreamBugTask(IHasProductAndAssignee):
    """A bug assigned to upstream, which is read-only by the current
    user."""
    pass

class IEditableDistroBugTask(Interface):
    """A bug assigned to a distro package, which is editable by
    the current user."""
    pass

class IReadOnlyDistroBugTask(Interface):
    """A bug assigned to a distro package, which is read-only by the
    current user."""
    pass

class IBugTaskSet(Interface):
    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get an IBugTask."""

    def __iter__():
        """Iterate through IBugTasks for a given bug."""

class IBugsAssignedReport(Interface):

    user = Attribute(_("The user for whom this report will be generated"))

    minseverity = Attribute(_("""The minimum severity of assignments to
        display in this report."""))

    minpriority = Attribute(_("""The minimum priority of bug fixing
        assignments to display in this report."""))

    showclosed = Attribute(_("""Whether or not to show closed bugs on this
        report."""))

    def maintainedPackageBugs():
        """Return an iterator over the assignments of bugs to distro
        packages the user maintains."""

    def maintainedProductBugs():
        """Return an iterator over the assignments of bugs to upstream
        products the user maintains."""

    def productAssigneeBugs():
        """Return an iterator over the bugassignments to upstream products
        which are assigned directly to the user."""

    def packageAssigneeBugs():
        """Return an iterator over the bugassignments to distro packages
        which are assigned directly to the user."""

    def assignedBugs():
        """An iterator over ALL the bugs directly or indirectly assigned
        to the person."""
