
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')
from zope.interface import Interface, Attribute

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.app.form.browser.interfaces import IAddFormCustomization

from canonical.lp import dbschema

class IEditableUpstreamBugTask(Interface):
    pass

class IReadOnlyUpstreamBugTask(Interface):
    pass

class ISourcePackageBugTask(Interface):
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
