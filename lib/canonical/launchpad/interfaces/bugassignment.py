
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')
from zope.interface import Interface, Attribute

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.app.form.browser.interfaces import IAddFormCustomization

from canonical.lp import dbschema

#
# Bug Upstream Assignments
#
class IProductBugAssignment(Interface):
    """The status of a bug with regard to a product."""

    id = Int(title=_('ID'), required=True, readonly=True)
    bug = Int(title=_('Bug ID'), required=True, readonly=True)
    product = Choice(title=_('Product'), required=True, vocabulary='Product')
    bugstatus = Choice(title=_('Bug Status'), vocabulary='BugStatus')
    priority = Choice(title=_('Priority'), vocabulary='BugPriority')
    severity = Choice(title=_('Severity'), vocabulary='BugSeverity')
    assignee = Choice(title=_('Assignee'), required=False, vocabulary='Person')
    datecreated = Datetime(title=_('Date Created'), required=True,
                           readonly=True)
    ownerID = Int(
            title=_('Owner'), required=True, readonly=True
            )
    # XXX: Need to define a proper schema type for owner to avoid this hack
    # and remove the need for the widget subdirective in the addform .zcml
    owner = Int(title=_('Owner'), required=True, readonly=True)
    #owner = Attribute("The owner's IPerson")


class IProductBugAssignmentContainer(Interface):
    """A container for IProductBugAssignment objects."""

    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get a ProductBugAssignment"""

    def __iter__():
        """Iterate through ProductBugAssignments for a given bug."""

#
# Bug Assignments to Distro Packages
#

class ISourcePackageBugAssignment(Interface):
    """The status of a bug with regard to a source package."""

    id = Int(title=_('ID'), required=True, readonly=True)
    bug = Int(title=_('Bug ID'), required=True, readonly=True)
    sourcepackage = Choice(
            title=_('Source Package'), required=True, readonly=True,
            vocabulary='SourcePackage'
            )
    bugstatus = Choice(
            title=_('Bug Status'), vocabulary='BugStatus',
            required=True, default=int(dbschema.BugAssignmentStatus.NEW),
            )
    priority = Choice(
            title=_('Priority'), vocabulary='BugPriority',
            required=True, default=int(dbschema.BugPriority.MEDIUM),
            )
    severity = Choice(
            title=_('Severity'), vocabulary='BugSeverity',
            required=True, default=int(dbschema.BugSeverity.NORMAL),
            )
    binarypackagename = Choice(
            title=_('Binary PackageName'), required=False,
            vocabulary='BinaryPackageName'
            )
    assignee = Choice(title=_('Assignee'), required=False, vocabulary='Person')
    datecreated = Datetime(title=_('Date Created'), required=True,
                           readonly=True)
    ownerID = Int(
            title=_('Owner'), required=True, readonly=True
            )
    # XXX: Need to define a proper schema type for owner to avoid this hack
    # and remove the need for the widget subdirective in the addform .zcml
    owner = Int(title=_('Owner'), required=True, readonly=True)
    #owner = Attribute("The owner's IPerson")


class ISourcePackageBugAssignmentContainer(Interface):
    """A container for ISourcePackageBugAssignment objects."""

    bug = Int(title=_("Bug id"), readonly=True)

    def __getitem__(key):
        """Get a SourcePackageBugAssignment"""

    def __iter__():
        """Iterate through SourcePackageBugAssignments for a given bug."""


#
# Bug Report Objects
#


class IBugsAssignedReport(Interface):

    user = Attribute(_("The user for whom this report will be generated"))

    minseverity = Attribute(_("""The minimum severity of assignments to
        display in this report."""))

    def assignedBugs():
        """An iterator over ALL the bugs directly or indirectly assigned
        to the person."""


